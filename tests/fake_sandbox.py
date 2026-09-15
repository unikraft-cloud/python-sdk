# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# An in-memory sandbox plugin behind an instance's plugin route, plus just
# enough of the platform API -- metros and instance lookups -- for a handle to
# resolve the route. The handler is async so the unbounded `wait` can block the
# way the real one does, and finish when the command does.

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import httpx

from .conftest import Recorder, envelope, instance, metro, metro_of

#: Signals that count as an interrupt a command heeds, by number or name, and
#: the number each one stands for.
_INTERRUPTS: dict[int | str, int] = {2: 2, 15: 15, "INT": 2, "SIGINT": 2, "TERM": 15, "SIGTERM": 15}


def empty_envelope() -> dict[str, Any]:
    """The envelope of an operation that carries no data: `data` is null."""
    return {"status": "success", "data": None, "op_time_us": 1}


def error_envelope(status: int, message: str) -> dict[str, Any]:
    return {"status": "error", "message": message, "errors": [{"status": status}], "op_time_us": 1}


class FakeCommand:
    """One command's state: what it was started with, its output, and its end."""

    def __init__(
        self,
        uuid: str,
        cmdline: str,
        cwd: str | None,
        env: dict[str, str] | None,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
        exit_code: int = 0,
        exits_after_polls: int = 0,
        heeds_interrupt: bool = True,
    ) -> None:
        self.uuid = uuid
        self.cmdline = cmdline
        self.cwd = cwd
        self.env = env
        self.stdout = stdout
        self.stderr = stderr
        #: The exit code the command ends with on its own.
        self.exit_code = exit_code
        #: How many output polls it survives before ending on its own; 0 ends
        #: it as soon as it starts, and a very large number never does.
        self.exits_after_polls = exits_after_polls
        self.heeds_interrupt = heeds_interrupt
        self.exitcode: int | None = None
        self.exited = asyncio.Event()
        self.polls = 0
        self.stdin: list[tuple[bytes, bool]] = []
        self.signals: list[int | str] = []
        self.logs_deleted = False

    def finish(self, code: int) -> None:
        self.exitcode = code
        self.exited.set()

    @property
    def running(self) -> bool:
        return self.exitcode is None


class FakeSandbox:
    """A sandbox plugin on one instance, answering over a recording transport.

    Register how the next started command behaves with :meth:`on_run`; a
    command started without a script ends at once with exit code 0 and no output.
    """

    def __init__(
        self,
        *,
        uuid: str = "u1",
        name: str = "web",
        plugin: str = "sandbox",
        metros: tuple[str, ...] = ("fra", "dal"),
        instance_metro: str = "fra",
    ) -> None:
        self.uuid = uuid
        self.name = name
        self.plugin = plugin
        self.prefix = f"/v1/instances/{uuid}/plugins/{plugin}"
        self.metros = metros
        #: The metro that holds the instance; other metros report no match.
        self.instance_metro = instance_metro
        self.instance = instance(uuid, name)
        self.commands: dict[str, FakeCommand] = {}
        self.scripts: list[dict[str, Any]] = []
        self.files: dict[str, bytes] = {}
        self.dirs: list[tuple[str, bool]] = []
        #: How many readiness probes fail before the plugin answers, and how.
        self.unready = 0
        self.unready_status = 503
        #: How many output polls fail before they succeed again.
        self.failing_polls = 0
        #: How many signals fail before they work again, how many writes to a
        #: command's standard input, and how many reads of a command.
        self.failing_signals = 0
        self.failing_stdin = 0
        self.failing_reads = 0
        self.recorder = Recorder(self.handle)
        self._next = 1

    @property
    def transport(self) -> httpx.MockTransport:
        return self.recorder.transport

    def on_run(self, **behaviour: Any) -> None:
        """How the next started command behaves; see :class:`FakeCommand`."""
        self.scripts.append(behaviour)

    def plugin_paths(self) -> list[str]:
        """The plugin-route paths requested, relative to the route."""
        return [p[len(self.prefix) :] for p in self.recorder.paths if p.startswith(self.prefix)]

    # -- the handler ---------------------------------------------------------

    async def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/metros":
            return _json(200, envelope({"metros": [metro(code) for code in self.metros]}))
        if path in ("/v1/instances", "/v1/instances/wait"):
            return self._platform_instances(request)
        if path == self.prefix or path.startswith(self.prefix + "/"):
            return await self._plugin(request, path[len(self.prefix) :])
        return _json(404, error_envelope(404, f"no route for {path}"))

    def _platform_instances(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return _json(200, envelope({"instances": [self.instance]}))
        params = request.url.params
        matches = params.get("uuid") in (None, self.uuid) and params.get("name") in (
            None,
            self.name,
        )
        if metro_of(request) != self.instance_metro or not matches:
            return _json(200, envelope({"instances": []}))
        if request.url.path.endswith("/wait"):
            waited = {"uuid": self.uuid, "name": self.name, "state": "running"}
            return _json(200, envelope({"instances": [waited]}))
        return _json(200, envelope({"instances": [self.instance]}))

    async def _plugin(self, request: httpx.Request, sub: str) -> httpx.Response:
        method = request.method
        body: dict[str, Any] = json.loads(request.content) if request.content else {}

        if sub == "/commands" and method == "GET":
            if self.unready > 0:
                self.unready -= 1
                return _json(self.unready_status, error_envelope(self.unready_status, "not yet"))
            return _json(200, envelope({"commands": list(self.commands)}))
        if sub == "/commands" and method == "POST":
            return self._run(body)

        if sub.startswith("/commands/"):
            parts = sub[len("/commands/") :].split("/")
            command = self.commands.get(parts[0])
            if command is None:
                return httpx.Response(404)
            rest = "/".join(parts[1:])
            return await self._command(request, command, rest, body)

        if sub.startswith("/fs/") and method == "POST":
            return self._fs(sub[len("/fs/") :], body)
        return httpx.Response(404)

    def _run(self, body: dict[str, Any]) -> httpx.Response:
        uuid = f"c{self._next}"
        self._next += 1
        script = self.scripts.pop(0) if self.scripts else {}
        command = FakeCommand(uuid, body["cmd"], body.get("cwd"), body.get("env"), **script)
        self.commands[uuid] = command
        if command.exits_after_polls == 0:
            command.finish(command.exit_code)
        return _json(200, envelope({"uuid": uuid}))

    async def _command(
        self, request: httpx.Request, command: FakeCommand, op: str, body: dict[str, Any]
    ) -> httpx.Response:
        method = request.method
        if op == "" and method == "GET":
            if self.failing_reads > 0:
                self.failing_reads -= 1
                return _json(500, error_envelope(500, "read lost"))
            return _json(
                200,
                envelope(
                    {
                        "uuid": command.uuid,
                        "cmdline": command.cmdline,
                        "cwd": command.cwd,
                        "env": command.env,
                        "exitcode": command.exitcode,
                    }
                ),
            )
        if op == "" and method == "DELETE":
            if command.running:
                return _json(409, error_envelope(409, "still running"))
            del self.commands[command.uuid]
            return _json(200, empty_envelope())
        if op == "logs" and method == "DELETE":
            command.logs_deleted = True
            return _json(200, empty_envelope())
        if op == "logs" and method == "GET":
            return self._logs(command, body)
        if op.startswith("logs/raw/"):
            return self._raw_log(command, op[len("logs/raw/") :], request.headers.get("range"))
        if op == "stdin":
            if command.logs_deleted:
                return httpx.Response(410)
            if self.failing_stdin > 0:
                self.failing_stdin -= 1
                return _json(502, error_envelope(502, "bad gateway"))
            # As the plugin: a close after the end is fine, data for an ended command is not.
            if not command.running and not (body.get("eof") and not body["data"]):
                return _json(410, error_envelope(410, "Command logs deleted"))
            command.stdin.append((base64.b64decode(body["data"]), bool(body.get("eof"))))
            return _json(200, empty_envelope())
        if op == "signal":
            if self.failing_signals > 0:
                self.failing_signals -= 1
                return _json(500, error_envelope(500, "signal lost"))
            signal = body["signal"]
            command.signals.append(signal)
            if command.heeds_interrupt and signal in _INTERRUPTS and command.running:
                # Ended by the signal, which the plugin reports as minus its number.
                command.finish(-_INTERRUPTS[signal])
            return _json(200, empty_envelope())
        if op == "wait":
            await command.exited.wait()
            return _json(200, empty_envelope())
        if op == "wait_timeout":
            try:
                await asyncio.wait_for(command.exited.wait(), body["timeout_s"])
            except asyncio.TimeoutError:
                return _json(408, error_envelope(408, "still running"))
            return _json(200, empty_envelope())
        return httpx.Response(404)

    def _logs(self, command: FakeCommand, body: dict[str, Any]) -> httpx.Response:
        if command.logs_deleted:
            return httpx.Response(410)
        if self.failing_polls > 0:
            self.failing_polls -= 1
            return _json(500, error_envelope(500, "flaky"))
        command.polls += 1
        if command.running and command.polls >= command.exits_after_polls:
            command.finish(command.exit_code)

        def part(data: bytes, spec: dict[str, Any] | None) -> str:
            spec = spec or {}
            offset = spec.get("offset", 0)
            limit = spec.get("limit")
            end = len(data) if limit is None else min(len(data), offset + limit)
            return base64.b64encode(data[offset:end]).decode()

        return _json(
            200,
            envelope(
                {
                    "stdout": part(command.stdout, body.get("stdout")),
                    "stderr": part(command.stderr, body.get("stderr")),
                    "stdout_available": len(command.stdout),
                    "stderr_available": len(command.stderr),
                }
            ),
        )

    def _raw_log(self, command: FakeCommand, stream: str, byte_range: str | None) -> httpx.Response:
        if command.logs_deleted:
            return httpx.Response(410)
        data = {"stdout": command.stdout, "stderr": command.stderr}.get(stream)
        if data is None:
            return httpx.Response(404)
        headers = {"content-type": "application/octet-stream"}
        if byte_range is None:
            return httpx.Response(200, content=data, headers=headers)
        start_s, _, end_s = byte_range.removeprefix("bytes=").partition("-")
        start = int(start_s)
        if start >= len(data):
            return httpx.Response(416, headers={"content-range": f"bytes */{len(data)}"})
        end = len(data) - 1 if end_s == "" else min(int(end_s), len(data) - 1)
        headers["content-range"] = f"bytes {start}-{end}/{len(data)}"
        return httpx.Response(206, content=data[start : end + 1], headers=headers)

    def _fs(self, op: str, body: dict[str, Any]) -> httpx.Response:
        if op == "mkdir":
            self.dirs.append((body["path"], body["parents"]))
            return _json(200, empty_envelope())
        if op == "read":
            data = self.files.get(body["path"])
            if data is None:
                return _json(500, error_envelope(500, "No such file or directory"))
            return _json(200, envelope({"contents": base64.b64encode(data).decode()}))
        if op == "read_raw":
            data = self.files.get(body["path"])
            if data is None:
                return httpx.Response(404)
            return httpx.Response(
                200, content=data, headers={"content-type": "application/octet-stream"}
            )
        if op == "write":
            path = body["path"]
            if path.rstrip("/") in {d for d, _ in self.dirs}:
                return _json(500, error_envelope(500, "Is a directory (os error 21)"))
            data = _decode(body)
            self.files[path] = self.files.get(path, b"") + data if body["append"] else data
            return _json(200, empty_envelope())
        return httpx.Response(404)


def _decode(body: dict[str, Any]) -> bytes:
    data: str = body["data"]
    return data.encode() if body["encoding"] == "utf-8" else base64.b64decode(data)


def _json(status: int, body: dict[str, Any]) -> httpx.Response:
    return httpx.Response(status, json=body)
