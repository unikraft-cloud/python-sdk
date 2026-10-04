# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The sandbox plugin: shell commands and files inside an instance, over the
# plugin's HTTP API. A command is started; while an unbounded wait for it
# runs alongside, its output is polled, quickly while output arrives and
# backing off while it does not; and a timeout interrupts the command and
# then waits for it to end.

from __future__ import annotations

import asyncio
import base64
import contextlib
import inspect
import json
import os
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, TypeVar

import httpx

from ..api.plugins.sandbox import PLUGIN_NAME, SandboxApi, models
from ..core.errors import AuthenticationError, ErrorKind, UnikraftCloudError
from ..core.fanout import AmbiguousRefError, MetroFanoutError
from ..core.handle import spent
from . import Plugin

__all__ = [
    "INTERRUPT_SIGNAL",
    "LOG_CHUNK_SIZE",
    "PLUGIN_NAME",
    "POLL_INTERVAL",
    "POLL_MAX_FAILURES",
    "POLL_MAX_INTERVAL",
    "READY_FIRST_INTERVAL",
    "READY_MAX_INTERVAL",
    "STDIN_CHUNK_SIZE",
    "WRITE_CHUNK_SIZE",
    "Command",
    "CommandLogs",
    "ExecResult",
    "ExecTimeoutError",
    "OutputChunk",
    "OutputSink",
    "OutputStream",
    "PluginNotReadyError",
    "Sandbox",
    "SandboxFiles",
]

#: How long :meth:`Sandbox.wait_ready` waits before its second probe, and the
#: most it waits between two. The wait doubles from the first to the second.
READY_FIRST_INTERVAL = 0.25
READY_MAX_INTERVAL = 2.0
#: How often a running command's output is polled: this often while output
#: arrives, doubling up to the cap while it does not.
POLL_INTERVAL = 0.1
POLL_MAX_INTERVAL = 1.0
#: How many consecutive failed polls give up on a command's output.
POLL_MAX_FAILURES = 3
#: How much of each output stream one poll asks for, in bytes.
LOG_CHUNK_SIZE = 1 << 20
#: How much standard input one request carries, in bytes.
STDIN_CHUNK_SIZE = 32 << 10
#: How many bytes of a file one write request carries, text counted as JSON
#: escapes it. The plugin reads two mebibytes of body at most; base64 adds a third.
WRITE_CHUNK_SIZE = 1 << 20
#: The signal a command is sent when its caller's timeout elapses: SIGINT.
INTERRUPT_SIGNAL = 2
#: How long the interrupt itself is given to be delivered.
_SIGNAL_TIMEOUT = 5.0

# Named so tests can stand in for it and assert the backoff without waiting.
_sleep = asyncio.sleep

#: One of a command's two output streams.
OutputStream = Literal["stdout", "stderr"]


class PluginNotReadyError(UnikraftCloudError, TimeoutError):
    """The plugin did not answer within the time allowed.

    An :class:`UnikraftCloudError` and a builtin :class:`TimeoutError` both, as
    :class:`~unikraft_cloud.WaitTimeoutError` is, so one ``except`` catches
    every SDK failure and another every timeout. The last failure is chained
    as the cause. A plugin that never answers is often an instance that is not
    running; the plugin cannot say so itself, so a caller that wants to tell
    the two apart reads the instance's state.
    """

    def __init__(
        self, message: str, *, plugin: str, attempts: int, kind: ErrorKind = "http"
    ) -> None:
        super().__init__(message, kind=kind)
        #: The plugin that was probed.
        self.plugin = plugin
        #: How many probes were made.
        self.attempts = attempts


class ExecTimeoutError(UnikraftCloudError, TimeoutError):
    """A command ran past its timeout and is still running.

    Raised when the interrupt a timeout sends could not be delivered, or when
    a grace period was given and the command outlived it, and the command has
    not ended by itself either. It is left as it is, so the caller can signal
    or inspect it. An :class:`UnikraftCloudError` and a builtin
    :class:`TimeoutError` both.
    """

    def __init__(self, command: Command) -> None:
        super().__init__(f"command {command.uuid} is still running", kind="http")
        #: The command, still running in the sandbox.
        self.command = command


@dataclass(frozen=True)
class OutputChunk:
    """A piece of a command's output, as it arrived."""

    #: Which stream it came from.
    stream: OutputStream
    #: The bytes, decoded from the wire.
    data: bytes


#: Where a command's output goes as it arrives: called with each chunk. It may
#: return an awaitable, awaited before the next chunk is read; any other
#: return value, such as the count a file's ``write`` reports, is ignored.
OutputSink = Callable[[OutputChunk], "Awaitable[None] | object | None"]


@dataclass(frozen=True)
class CommandLogs:
    """The requested parts of a command's two output streams."""

    stdout: bytes
    stderr: bytes
    #: How many bytes each stream holds in total.
    stdout_available: int
    stderr_available: int


@dataclass(frozen=True)
class ExecResult:
    """A finished command: its exit code and everything it wrote."""

    uuid: str
    #: The exit code, or minus the signal number when a signal ended the command:
    #: ``-2`` after the interrupt that a timeout sends.
    exit_code: int
    stdout: bytes
    stderr: bytes
    #: Whether an interrupt was sent because the timeout elapsed. The command
    #: may have ended on its own regardless; ``exit_code`` says how it ended.
    interrupted: bool = False


D = TypeVar("D")


def _payload(data: D | None, what: str) -> D:
    """The payload of an envelope, or a parse error when the plugin sent none.

    The wire models keep every field optional, so an answer that arrived
    without its payload is caught here, where it can be named, rather than
    at the first attribute read.
    """
    if data is None:
        raise UnikraftCloudError(f"the plugin answered {what} without a payload", kind="parse")
    return data


class Sandbox:
    """The sandbox plugin on one instance.

    Obtained from an instance handle with :meth:`~InstanceHandle.sandbox`. The
    route is resolved on first use, so building one sends nothing.

    .. code-block:: python

        sb = ukc.metro("fra").instances.get(uuid=uuid).sandbox()
        await sb.wait_ready(timeout=60)
        result = await sb.exec("make test", cwd="/app")
        print(result.exit_code, result.stdout.decode())
    """

    def __init__(self, plugin: Plugin) -> None:
        #: The plugin this client speaks to.
        self.plugin = plugin
        #: The sandbox filesystem.
        self.fs = SandboxFiles(self)
        self._api: asyncio.Future[SandboxApi] | None = None

    async def api(self) -> SandboxApi:
        """The raw plumbing client, pointed at the plugin's route.

        Built once and shared. A build the caller waiting on it gave up on
        runs on and serves the next call; one that failed is not kept, so the
        next call builds it again.
        """
        if spent(self._api):
            self._api = asyncio.ensure_future(self.plugin.client(SandboxApi))
        assert self._api is not None
        return await asyncio.shield(self._api)

    async def ready(self) -> bool:
        """Whether the plugin is up and serving, by listing its commands.

        A failure means it is not: either not yet, or not any more. An
        instance that cannot be found counts as a plugin not answering. A
        failure that waiting cannot change -- a rejected token, a name that
        several instances hold -- is raised instead.
        """
        try:
            api = await self.api()
            await api.commands.list_commands()
        except UnikraftCloudError as err:
            if _permanent(err):
                raise
            return False
        return True

    async def wait_ready(self, timeout: float = 60.0) -> None:
        """Block until the plugin answers, or raise :class:`PluginNotReadyError`.

        Probes with a backoff that starts at :data:`READY_FIRST_INTERVAL` and
        settles at :data:`READY_MAX_INTERVAL`, so a plugin that comes up quickly
        is not waited on longer than it takes, and one that never comes up is not
        hammered. Locating the instance counts against ``timeout`` too, and an
        instance not found yet is probed again like a plugin not up yet, so one
        call also waits out an instance still being created, and each probe's
        read is bounded by what is left of ``timeout``. A ``timeout`` of zero
        or less makes exactly one attempt. A failure that cannot change
        with time is not waited out: a rejected token or a name that several
        instances hold is raised at once, and a create that failed, whose
        outcome the handle keeps, at the next probe.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        interval = READY_FIRST_INTERVAL
        attempts = 0
        last: UnikraftCloudError | None = None
        while True:
            attempts += 1
            try:
                api = await self.api()
                await api.commands.list_commands(
                    timeout=_probe_timeout(api.client.config.timeout, deadline - loop.time())
                )
                return
            except UnikraftCloudError as err:
                # A memoised failure returns the same error object again; waiting
                # does not change it or the errors that `_permanent` names.
                if err is last or _permanent(err):
                    raise
                last = err
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise PluginNotReadyError(
                    f"plugin {self.plugin.name!r} did not answer within {timeout}s "
                    f"({attempts} attempts)",
                    plugin=self.plugin.name,
                    attempts=attempts,
                    kind=last.kind,
                ) from last
            await _sleep(min(interval, remaining))
            interval = min(interval * 2, READY_MAX_INTERVAL)

    async def run(
        self,
        cmd: str | Sequence[str],
        *,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> Command:
        """Start a command and return a handle on it.

        A ``str`` is a command line the sandbox's shell interprets. A sequence
        is an argument vector run as it is, with no shell and nothing to quote,
        which is the form to use with paths or arguments from elsewhere.
        ``cwd`` and ``env`` are passed on exactly as given; the plugin defines
        what a command sees when they are omitted.
        """
        fields: dict[str, Any] = {}
        if cwd is not None:
            fields["cwd"] = cwd
        if env is not None:
            fields["env"] = dict(env)
        line: str | list[str] = cmd if isinstance(cmd, str) else list(cmd)
        api = await self.api()
        res = await api.commands.run_command(body=models.RunCommandRequest(cmd=line, **fields))
        started = _payload(res.data, "a command start")
        if not started.uuid:
            raise UnikraftCloudError("the plugin started a command but named no UUID", kind="parse")
        return Command(self, started.uuid)

    async def commands(self) -> list[Command]:
        """Every command the plugin knows of, in the order they were started."""
        api = await self.api()
        res = await api.commands.list_commands()
        listed = _payload(res.data, "the command listing")
        return [Command(self, uuid) for uuid in listed.commands or []]

    def command(self, uuid: str) -> Command:
        """A handle on a command started earlier, by its UUID."""
        return Command(self, uuid)

    async def exec(
        self,
        cmd: str | Sequence[str],
        *,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        stdin: bytes | str | None = None,
        timeout: float | None = None,
        wait_delay: float | None = None,
        on_output: OutputSink | None = None,
        forget: bool = False,
    ) -> ExecResult:
        """Run a command to completion and return its output and exit code.

        ``cmd`` is a command line for the shell, or an argument vector, as for
        :meth:`run`. A non-zero exit code is reported, not raised. See
        :meth:`Command.collect` for what the other arguments do.

        .. code-block:: python

            result = await sb.exec(
                "make test",
                cwd="/app",
                timeout=600,
                on_output=lambda chunk: print(chunk.data.decode(errors="replace"), end=""),
                forget=True,
            )
        """
        _check_following(timeout, wait_delay)
        # Encoded before the command starts, so a `str` that cannot be is refused first.
        if isinstance(stdin, str):
            stdin = stdin.encode()
        command = await self.run(cmd, cwd=cwd, env=env)
        return await command.collect(
            stdin=stdin,
            timeout=timeout,
            wait_delay=wait_delay,
            on_output=on_output,
            forget=forget,
        )


class Command:
    """A shell command running, or finished, inside a sandbox."""

    def __init__(self, sandbox: Sandbox, uuid: str) -> None:
        #: The sandbox the command runs in.
        self.sandbox = sandbox
        #: The UUID the plugin assigned it.
        self.uuid = uuid

    def __repr__(self) -> str:
        return f"Command({self.uuid!r})"

    async def get(self) -> models.GetCommandData:
        """The command line, working directory, environment and exit code.

        The exit code is ``None`` while the command still runs.
        """
        api = await self.sandbox.api()
        res = await api.commands.get_command_by_uuid(self.uuid)
        return _payload(res.data, f"command {self.uuid}")

    async def _exit_code(self) -> int:
        """The exit code of a command that has ended, read with a poll's patience."""
        failures = 0
        interval = POLL_INTERVAL
        while True:
            try:
                info = await self.get()
            except UnikraftCloudError:
                failures += 1
                if failures >= POLL_MAX_FAILURES:
                    raise
                await _sleep(interval)
                interval = min(interval * 2, POLL_MAX_INTERVAL)
                continue
            if info.exitcode is None:
                raise UnikraftCloudError(
                    f"command {self.uuid} ended without reporting an exit code", kind="parse"
                )
            return info.exitcode

    async def _ended(self) -> bool:
        """Whether the command has exited, by one read; a read that fails says no."""
        try:
            return (await self.get()).exitcode is not None
        except UnikraftCloudError:
            return False

    async def wait(self, timeout: float | None = None) -> int | None:
        """Wait for the command to end and return its exit code.

        With a ``timeout``, returns ``None`` if the command is still running
        when it elapses. Without one, blocks until the command ends.
        """
        _check_following(timeout, None)
        api = await self.sandbox.api()
        if timeout is None:
            await api.commands.wait_for_command(self.uuid)
        else:
            try:
                await api.commands.wait_for_command_with_timeout(
                    self.uuid, body=models.CommandWaitTimeoutRequest(timeout_s=timeout)
                )
            except UnikraftCloudError as err:
                if err.status == 408:
                    return None
                raise
        return await self._exit_code()

    async def logs(
        self,
        *,
        stdout_offset: int = 0,
        stderr_offset: int = 0,
        limit: int | None = None,
    ) -> CommandLogs:
        """The output collected so far, from the given offsets.

        Each stream is returned from its offset to its end, or for at most
        ``limit`` bytes. The totals say how much each stream holds, so a caller
        reading incrementally knows when it has everything.
        """
        api = await self.sandbox.api()
        ranges: dict[str, Any] = {} if limit is None else {"limit": limit}
        body = models.CommandLogsRequest(
            stdout=models.CommandLogsRange(offset=stdout_offset, **ranges),
            stderr=models.CommandLogsRange(offset=stderr_offset, **ranges),
        )
        res = await api.commands.get_command_logs(self.uuid, body=body)
        # A stream the plugin left out is one with nothing in it.
        logs = _payload(res.data, f"the logs of command {self.uuid}")
        return CommandLogs(
            stdout=base64.b64decode(logs.stdout or ""),
            stderr=base64.b64decode(logs.stderr or ""),
            stdout_available=logs.stdout_available or 0,
            stderr_available=logs.stderr_available or 0,
        )

    async def stdout(self) -> bytes:
        """The whole standard output stream, verbatim."""
        api = await self.sandbox.api()
        return (await api.commands.get_raw_command_log(self.uuid, "stdout")).content

    async def stderr(self) -> bytes:
        """The whole standard error stream, verbatim."""
        api = await self.sandbox.api()
        return (await api.commands.get_raw_command_log(self.uuid, "stderr")).content

    async def stream(self) -> AsyncGenerator[OutputChunk, None]:
        """Follow the command's output until it ends.

        An unbounded wait for the command runs alongside the polling, so the
        stream ends as soon as the command does, with whatever output remained.
        Polling backs off while the command is quiet and speeds back up when
        it writes; :data:`POLL_MAX_FAILURES` consecutive failed polls raise.
        """
        api = await self.sandbox.api()
        ended = asyncio.ensure_future(api.commands.wait_for_command(self.uuid))
        cursor = _OutputCursor()
        interval = POLL_INTERVAL
        failures = 0
        try:
            while True:
                if ended.done():
                    # A failed wait is the command's end too, just not a clean one.
                    ended.result()
                    # Drain what the polls have not read yet, forgiving a failed
                    # poll as the loop below does.
                    while True:
                        try:
                            chunks = await self._poll(api, cursor)
                        except UnikraftCloudError:
                            failures += 1
                            if failures >= POLL_MAX_FAILURES:
                                raise
                            await _sleep(interval)
                            interval = min(interval * 2, POLL_MAX_INTERVAL)
                            continue
                        failures = 0
                        for chunk in chunks:
                            yield chunk
                        if not chunks or cursor.drained:
                            return
                try:
                    chunks = await self._poll(api, cursor)
                except UnikraftCloudError:
                    failures += 1
                    if failures >= POLL_MAX_FAILURES:
                        raise
                    interval = min(interval * 2, POLL_MAX_INTERVAL)
                else:
                    failures = 0
                    for chunk in chunks:
                        yield chunk
                    interval = POLL_INTERVAL if chunks else min(interval * 2, POLL_MAX_INTERVAL)
                # Sleep out the interval, but wake as soon as the command ends.
                await asyncio.wait({ended}, timeout=interval)
        finally:
            if not ended.done():
                ended.cancel()
                with contextlib.suppress(asyncio.CancelledError, UnikraftCloudError):
                    await ended
            elif not ended.cancelled():
                # A wait that failed after it was last looked at is read here,
                # or the loop would report its error as never retrieved.
                ended.exception()

    async def _poll(self, api: SandboxApi, cursor: _OutputCursor) -> list[OutputChunk]:
        """Read what each stream has written since the cursor, and advance it."""
        body = models.CommandLogsRequest(
            stdout=models.CommandLogsRange(offset=cursor.stdout, limit=LOG_CHUNK_SIZE),
            stderr=models.CommandLogsRange(offset=cursor.stderr, limit=LOG_CHUNK_SIZE),
        )
        res = await api.commands.get_command_logs(self.uuid, body=body)
        logs = _payload(res.data, f"the logs of command {self.uuid}")
        cursor.stdout_available = logs.stdout_available or 0
        cursor.stderr_available = logs.stderr_available or 0
        chunks: list[OutputChunk] = []
        if logs.stdout:
            data = base64.b64decode(logs.stdout)
            cursor.stdout += len(data)
            chunks.append(OutputChunk("stdout", data))
        if logs.stderr:
            data = base64.b64decode(logs.stderr)
            cursor.stderr += len(data)
            chunks.append(OutputChunk("stderr", data))
        return chunks

    async def collect(
        self,
        *,
        stdin: bytes | str | None = None,
        timeout: float | None = None,
        wait_delay: float | None = None,
        on_output: OutputSink | None = None,
        forget: bool = False,
    ) -> ExecResult:
        """Follow the command to its end and return its output and exit code.

        ``stdin``, when given, is fed to the command in chunks and then closed.
        A feed that fails ends the collection with its error: a command left
        waiting for input that never comes might never end. ``on_output`` is
        handed each piece of output as it arrives, beside its being collected
        for the result.

        When ``timeout`` elapses the command is interrupted with
        :data:`INTERRUPT_SIGNAL` and then waited for, so a command that heeds
        the interrupt still reports its exit code, marked ``interrupted``. With
        ``wait_delay`` as well, a command that ignores the interrupt is given up
        on after that long, and :class:`ExecTimeoutError` is raised with it
        attached; the same is raised at once when the interrupt could not be
        sent, since nothing would end the command. A command found to have
        ended by itself in the meantime is followed to the end of its output
        instead. ``wait_delay`` needs a ``timeout`` to follow.

        ``forget`` drops the plugin's record of the command once it has ended,
        as :meth:`delete` would; otherwise the record stays until it is deleted.
        A command still running when the collection gives up is kept either way,
        and so is one left behind when this call fails or is cancelled: the
        command runs on in the sandbox, with its record, for the caller to
        signal or forget.
        """
        _check_following(timeout, wait_delay)
        # Encoded here, so a `str` that cannot be is refused before anything is sent.
        payload = stdin.encode() if isinstance(stdin, str) else stdin
        stdout, stderr = bytearray(), bytearray()

        async def consume() -> None:
            # Closed on the spot when the collection ends early, rather than
            # whenever the generator is collected.
            async with contextlib.aclosing(self.stream()) as chunks:
                async for chunk in chunks:
                    (stdout if chunk.stream == "stdout" else stderr).extend(chunk.data)
                    if on_output is not None:
                        handed = on_output(chunk)
                        if inspect.isawaitable(handed):
                            await handed

        feeder = None if payload is None else asyncio.ensure_future(self.feed_stdin(payload))
        consumer = asyncio.ensure_future(consume())
        following = asyncio.ensure_future(_followed(self, consumer, feeder))
        interrupted = False
        try:
            if timeout is None:
                await following
            else:
                try:
                    await asyncio.wait_for(asyncio.shield(following), timeout)
                except asyncio.TimeoutError:
                    interrupted = True
                    await self._cut_short(following, wait_delay)
        finally:
            tasks = [task for task in (following, consumer, feeder) if task is not None]
            pending = [task for task in tasks if not task.done()]
            for task in pending:
                task.cancel()
            # Gathered rather than awaited one by one under a suppression: the
            # tasks' own cancellations are results here, while a cancellation of
            # this call arriving now still propagates.
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            # A task that failed after the collection last looked at it is read
            # here, or the loop would report its error as never retrieved.
            for task in tasks:
                if not task.cancelled():
                    task.exception()
        exit_code = await self._exit_code()
        if forget:
            # The command has ended, however it ended, so the record can go. A
            # refusal to drop it does not fail a collection that succeeded.
            with contextlib.suppress(UnikraftCloudError):
                await self.delete()
        return ExecResult(
            uuid=self.uuid,
            exit_code=exit_code,
            stdout=bytes(stdout),
            stderr=bytes(stderr),
            interrupted=interrupted,
        )

    async def _cut_short(self, following: asyncio.Future[None], wait_delay: float | None) -> None:
        """Interrupt a command past its timeout, then wait out the grace for its end.

        A command that cannot be interrupted, or outlives the grace, is left
        running and raised as :class:`ExecTimeoutError`; one that has ended by
        itself in the meantime is followed to the end of its output instead.
        """
        failure = await self._interrupt()
        if failure is not None:
            # Nothing is on its way to end the command, so waiting for its
            # end would be waiting for nothing, unless it has ended already.
            if not await self._ended():
                raise ExecTimeoutError(self) from failure
        elif wait_delay is not None:
            try:
                await asyncio.wait_for(asyncio.shield(following), wait_delay)
                return
            except asyncio.TimeoutError:
                if not await self._ended():
                    raise ExecTimeoutError(self) from None
        await following

    async def _interrupt(self) -> Exception | None:
        """Send the interrupt, giving it a bounded time to be delivered.

        Returns what went wrong when it could not be sent, rather than raising:
        the caller decides what a command that cannot be interrupted means.
        """
        try:
            await asyncio.wait_for(self.signal(INTERRUPT_SIGNAL), _SIGNAL_TIMEOUT)
        except (asyncio.TimeoutError, UnikraftCloudError) as err:
            return err
        return None

    async def write_stdin(self, data: bytes | str, *, eof: bool = False) -> None:
        """Feed bytes into the command's standard input, in one request.

        ``eof`` closes standard input after the data. A ``str`` is sent UTF-8
        encoded.
        """
        api = await self.sandbox.api()
        payload = data.encode() if isinstance(data, str) else data
        body = models.CommandStdinRequest(data=base64.b64encode(payload).decode(), eof=eof)
        await api.commands.write_command_stdin(self.uuid, body=body)

    async def feed_stdin(self, data: bytes | str) -> None:
        """Feed all of ``data`` to standard input, a chunk per request, then close it."""
        payload = data.encode() if isinstance(data, str) else data
        for start in range(0, len(payload), STDIN_CHUNK_SIZE):
            await self.write_stdin(payload[start : start + STDIN_CHUNK_SIZE])
        await self.close_stdin()

    async def close_stdin(self) -> None:
        """Close the command's standard input."""
        await self.write_stdin(b"", eof=True)

    async def signal(self, signal: int | str) -> None:
        """Send a signal, by number or by name with or without the ``SIG`` prefix."""
        api = await self.sandbox.api()
        await api.commands.signal_command(
            self.uuid, body=models.CommandSignalRequest(signal=signal)
        )

    async def delete(self) -> None:
        """Forget the command. It must have ended; the plugin refuses otherwise.

        The refusal is a ``409``, raised as a plain :class:`UnikraftCloudError`
        that says the command still runs: wait for it or signal it first.
        """
        api = await self.sandbox.api()
        try:
            await api.commands.delete_command_by_uuid(self.uuid)
        except UnikraftCloudError as err:
            if err.status != 409:
                raise
            raise UnikraftCloudError(
                f"command {self.uuid} is still running, so the plugin keeps its record; "
                "wait for it or signal it first",
                kind="http",
                status=409,
                errors=err.errors,
                body=err.body,
            ) from err

    async def delete_logs(self) -> None:
        """Forget the command's output, freeing memory in the sandbox.

        Forgetting the output of a running command closes its pipes, which may
        make it fail. Reading the output afterwards is answered with ``410``.
        """
        api = await self.sandbox.api()
        await api.commands.delete_command_logs_by_uuid(self.uuid)


def _probe_timeout(timeout: float | httpx.Timeout | None, remaining: float) -> float:
    """A probe's timeout: the client's read bounded by what is left, a second at least."""
    current = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
    read = remaining if current.read is None else min(current.read, remaining)
    return max(read, 1.0)


async def _followed(
    command: Command, consumer: asyncio.Future[None], feeder: asyncio.Future[None] | None
) -> None:
    """Await the consumer, unless the feed fails while the command runs, which raises first.

    A feed the plugin refuses because the command has ended already is no
    failure of the collection: the command's own exit code tells that story.
    """
    tasks = {consumer} if feeder is None else {consumer, feeder}
    while True:
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        if consumer in done:
            return consumer.result()
        for task in done:
            try:
                task.result()
            except UnikraftCloudError:
                if not await command._ended():
                    raise


def _check_following(timeout: float | None, wait_delay: float | None) -> None:
    """Refuse a timeout, or a grace after it, that makes no sense, before anything is sent."""
    if timeout is not None and timeout < 0:
        raise ValueError("`timeout` is a number of seconds, zero or more, or None.")
    if wait_delay is None:
        return
    if timeout is None:
        raise TypeError("`wait_delay` is the grace after `timeout` elapses; give a `timeout` too.")
    if wait_delay < 0:
        raise ValueError("`wait_delay` is a number of seconds, zero or more, or None.")


class _OutputCursor:
    """How far each output stream has been read, and how much of it exists."""

    def __init__(self) -> None:
        self.stdout = 0
        self.stderr = 0
        self.stdout_available = 0
        self.stderr_available = 0

    @property
    def drained(self) -> bool:
        return self.stdout_available <= self.stdout and self.stderr_available <= self.stderr


class SandboxFiles:
    """The filesystem inside a sandbox."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    async def mkdir(self, path: str, *, parents: bool = False) -> None:
        """Create a directory, and with ``parents`` any missing directory above it."""
        api = await self._sandbox.api()
        await api.fs.create_directory(body=models.MkdirRequest(path=path, parents=parents))

    async def read(self, path: str) -> bytes:
        """The contents of a file, verbatim."""
        api = await self._sandbox.api()
        return (await api.fs.read_raw_file(body=models.ReadFileRequest(path=path))).content

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """The contents of a text file."""
        return (await self.read(path)).decode(encoding)

    async def stream(
        self, path: str, *, chunk_size: int | None = None
    ) -> AsyncGenerator[bytes, None]:
        """The contents of a file as they arrive, for one too large to hold whole.

        Leave the loop to stop early; the connection is released when the
        generator is closed, which ``contextlib.aclosing`` does on the spot.
        """
        if chunk_size is not None:
            _check_chunk_size(chunk_size)
        api = await self._sandbox.api()
        # The generated `read_raw_file` answers with the payload whole; the SDK
        # client it sends through can hand the same payload, from the same
        # route, over as it arrives.
        chunks = api.client.stream_bytes(
            method="POST",
            path="/fs/read_raw",
            body=models.ReadFileRequest(path=path),
            chunk_size=chunk_size,
        )
        try:
            async for chunk in chunks:
                yield chunk
        finally:
            await chunks.aclose()

    async def read_to(
        self, path: str, local: str | os.PathLike[str], *, chunk_size: int | None = None
    ) -> int:
        """Copy a file out of the sandbox to a local path and return its size in bytes.

        The file is written as it arrives, so one larger than memory travels
        too. It is written beside ``local`` and moved into place once whole, so
        a download that fails leaves whatever was at ``local`` as it was.
        """
        if chunk_size is not None:
            _check_chunk_size(chunk_size)
        target = Path(local)
        partial = target.with_name(f".{target.name}.partial")
        size = 0
        try:
            with partial.open("wb") as handle:
                async with contextlib.aclosing(self.stream(path, chunk_size=chunk_size)) as chunks:
                    async for chunk in chunks:
                        await asyncio.to_thread(handle.write, chunk)
                        size += len(chunk)
            partial.replace(target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        return size

    async def write(
        self,
        path: str,
        data: bytes | str,
        *,
        append: bool = False,
        parents: bool = False,
        chunk_size: int = WRITE_CHUNK_SIZE,
    ) -> None:
        """Write a file, creating it if missing.

        ``bytes`` travel base64-encoded, and a ``str`` as UTF-8 when it fits one
        request, which are the two encodings the plugin accepts. ``append`` adds
        to the file instead of replacing it, and ``parents`` creates the
        directories above it first.

        The plugin bounds a request body, so data that does not fit
        ``chunk_size`` -- bytes by their count, text as JSON escapes it -- goes
        in that many bytes per request, base64-encoded: the first piece replaces
        the file, or with ``append`` adds to it, and the rest are appended to it.
        """
        _check_chunk_size(chunk_size)
        if parents:
            await self._make_parents(path)
        if _fits(data, chunk_size):
            await self._write(path, data, append=append)
            return
        payload = data.encode() if isinstance(data, str) else data
        for start in range(0, len(payload), chunk_size):
            piece = payload[start : start + chunk_size]
            await self._write(path, piece, append=append or start > 0)

    async def upload_file(
        self,
        local: str | os.PathLike[str],
        path: str,
        *,
        parents: bool = False,
        chunk_size: int = WRITE_CHUNK_SIZE,
    ) -> str:
        """Copy a local file into the sandbox and return the path it landed at.

        A ``path`` ending in ``/`` names a directory, and so does one the plugin
        reports to be one; the file keeps its name inside it. The file is read
        and sent ``chunk_size`` bytes at a time, so one larger than memory
        travels too. ``parents`` creates the directories above the target first.
        """
        _check_chunk_size(chunk_size)
        source = Path(local)
        target = f"{path}{source.name}" if path.endswith("/") else path
        if parents:
            await self._make_parents(target)
        try:
            await self._send_file(source, target, chunk_size)
        except UnikraftCloudError as err:
            if target != path or not _is_a_directory(err):
                raise
            # The path names a directory without its trailing slash.
            target = f"{path}/{source.name}"
            await self._send_file(source, target, chunk_size)
        return target

    async def _send_file(self, source: Path, target: str, chunk_size: int) -> None:
        """Send a local file in pieces: the first replaces the target, the rest append."""
        with source.open("rb") as handle:
            written = False
            while True:
                piece = await asyncio.to_thread(handle.read, chunk_size)
                if not piece and written:
                    break
                await self._write(target, piece, append=written)
                written = True
                if len(piece) < chunk_size:
                    break

    async def _write(self, path: str, data: bytes | str, *, append: bool) -> None:
        """One write request, with the data encoded the way the plugin takes it."""
        encoding, payload = _encode(data)
        api = await self._sandbox.api()
        await api.fs.write_file(
            body=models.WriteFileRequest(path=path, append=append, encoding=encoding, data=payload)
        )

    async def _make_parents(self, path: str) -> None:
        """Create the directories above ``path``."""
        parent = str(PurePosixPath(path).parent)
        if parent not in (".", "/"):
            await self.mkdir(parent, parents=True)

    async def upload(
        self,
        path: str,
        filename: str,
        data: bytes | str,
        *,
        parents: bool = False,
        chunk_size: int = WRITE_CHUNK_SIZE,
    ) -> str:
        """Write a file at ``path``, or at ``path/filename`` when ``path`` is a directory.

        A ``path`` ending in ``/`` names a directory, and so does one the plugin
        reports to be one, in which case the file goes inside it under
        ``filename``; the path the file landed at is returned. ``parents``
        creates the directories above it first, and the data travels as
        :meth:`write` sends it, which replaces a file that is there.
        """
        _check_chunk_size(chunk_size)
        if not filename or "/" in filename:
            raise ValueError("`filename` is one path segment: the file's name inside a directory.")
        target = f"{path}{filename}" if path.endswith("/") else path
        try:
            await self.write(target, data, parents=parents, chunk_size=chunk_size)
        except UnikraftCloudError as err:
            if target != path or not _is_a_directory(err):
                raise
            # The path names a directory without its trailing slash.
            target = f"{path}/{filename}"
            await self.write(target, data, parents=parents, chunk_size=chunk_size)
        return target


def _permanent(err: UnikraftCloudError) -> bool:
    """Whether waiting cannot change a failure: a rejected token, or a name held twice."""
    if isinstance(err, MetroFanoutError):
        # Every metro asked refused the token; one that could not answer may yet.
        return bool(err.failures) and all(
            isinstance(failure.error, AuthenticationError) for failure in err.failures
        )
    return isinstance(err, (AuthenticationError, AmbiguousRefError))


def _is_a_directory(err: UnikraftCloudError) -> bool:
    """Whether a write failed because its path is a directory, as the plugin reports it."""
    return err.status == 500 and "is a directory" in str(err).lower()


def _check_chunk_size(chunk_size: int) -> None:
    if chunk_size <= 0:
        raise ValueError("`chunk_size` is a number of bytes per request, one or more.")


def _fits(data: bytes | str, chunk_size: int) -> bool:
    """Whether the data goes in one request: bytes by their count, text as JSON escapes it."""
    if isinstance(data, str):
        return len(json.dumps(data)) <= chunk_size
    return len(data) <= chunk_size


def _encode(data: bytes | str) -> tuple[models.FileEncoding, str]:
    """Pick the wire encoding for file data: the plugin takes UTF-8 text or base64."""
    if isinstance(data, str):
        return "utf-8", data
    return "base64", base64.b64encode(data).decode()
