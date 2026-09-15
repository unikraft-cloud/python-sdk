# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The sandbox client against an in-memory plugin: readiness, commands and how
# they end, output following, and the filesystem. The polling intervals are
# shortened so a whole command lifecycle takes milliseconds.

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import httpx
import pytest

from unikraft_cloud import (
    AlreadyExistsError,
    AmbiguousRefError,
    AuthenticationError,
    ExecTimeoutError,
    MetroFanoutError,
    NotFoundError,
    OutputChunk,
    PluginNotReadyError,
    Sandbox,
    UnikraftCloud,
    UnikraftCloudError,
)
from unikraft_cloud.plugins import sandbox as sandbox_module

from .conftest import envelope
from .fake_sandbox import FakeCommand, FakeSandbox

NEVER = 10**9


@pytest.fixture(autouse=True)
def _quick_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox_module, "POLL_INTERVAL", 0.001)
    monkeypatch.setattr(sandbox_module, "POLL_MAX_INTERVAL", 0.002)


def cloud(fake: FakeSandbox) -> UnikraftCloud:
    return UnikraftCloud(token="tok", metro="fra", transport=fake.transport)


def sandbox(ukc: UnikraftCloud) -> Sandbox:
    return ukc.instances.get(uuid="u1").sandbox()


def body_of(fake: FakeSandbox, index: int) -> Any:
    return json.loads(fake.recorder.calls[index].content)


class Everywhere(FakeSandbox):
    """A platform whose every metro lists the instance."""

    def _platform_instances(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and not request.url.path.endswith("/wait"):
            return httpx.Response(200, json=envelope({"instances": [self.instance]}))
        return super()._platform_instances(request)


class TestReadiness:
    async def test_ready_is_whether_listing_commands_works(self) -> None:
        fake = FakeSandbox()
        fake.unready = 1
        async with cloud(fake) as ukc:
            sb = sandbox(ukc)
            assert await sb.ready() is False
            assert await sb.ready() is True

    async def test_ready_is_false_for_an_instance_that_cannot_be_found(self) -> None:
        fake = FakeSandbox(instance_metro="dal")
        async with cloud(fake) as ukc:
            # The client is pinned to fra, where no instance of that name is.
            assert await ukc.instances.get(name="web").sandbox().ready() is False
        assert fake.plugin_paths() == []

    async def test_wait_ready_returns_as_soon_as_the_plugin_answers(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            await sandbox(ukc).wait_ready(timeout=5)
        assert fake.plugin_paths() == ["/commands"]

    async def test_wait_ready_backs_off_from_a_quarter_second_to_two(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slept: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(sandbox_module, "_sleep", fake_sleep)
        fake = FakeSandbox()
        fake.unready = 5
        async with cloud(fake) as ukc:
            await sandbox(ukc).wait_ready(timeout=60)
        assert slept == [0.25, 0.5, 1.0, 2.0, 2.0]
        assert fake.plugin_paths() == ["/commands"] * 6

    async def test_a_route_not_found_yet_is_probed_again(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_sleep(seconds: float) -> None:
            pass

        # The proxy answers 404 while the plugin boots, and 502 or 504 once
        # it is routed but not yet serving.
        monkeypatch.setattr(sandbox_module, "_sleep", fake_sleep)
        fake = FakeSandbox()
        fake.unready, fake.unready_status = 2, 404
        async with cloud(fake) as ukc:
            await sandbox(ukc).wait_ready(timeout=60)
        assert fake.plugin_paths() == ["/commands"] * 3

    async def test_a_rejected_token_is_raised_at_once(self) -> None:
        fake = FakeSandbox()
        fake.unready, fake.unready_status = NEVER, 403
        async with cloud(fake) as ukc:
            with pytest.raises(AuthenticationError):
                await sandbox(ukc).wait_ready(timeout=60)
            with pytest.raises(AuthenticationError):
                await sandbox(ukc).ready()
        assert fake.plugin_paths() == ["/commands"] * 2

    async def test_a_name_held_by_several_instances_is_raised_at_once(self) -> None:
        fake = Everywhere()
        async with UnikraftCloud(token="tok", transport=fake.transport) as ukc:
            sb = ukc.instances.get(name="web").sandbox()
            with pytest.raises(AmbiguousRefError):
                await sb.wait_ready(timeout=60)
            with pytest.raises(AmbiguousRefError):
                await sb.ready()
        assert fake.plugin_paths() == []

    async def test_a_zero_timeout_makes_exactly_one_attempt(self) -> None:
        fake = FakeSandbox()
        fake.unready = 3
        async with cloud(fake) as ukc:
            with pytest.raises(PluginNotReadyError) as caught:
                await sandbox(ukc).wait_ready(timeout=0)
        assert (caught.value.plugin, caught.value.attempts) == ("sandbox", 1)
        assert isinstance(caught.value.__cause__, UnikraftCloudError)
        assert caught.value.__cause__.status == 503
        assert isinstance(caught.value, TimeoutError)

    async def test_wait_ready_gives_up_at_the_deadline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(sandbox_module, "_sleep", fake_sleep)
        fake = FakeSandbox()
        fake.unready = NEVER
        async with cloud(fake) as ukc:
            with pytest.raises(PluginNotReadyError) as caught:
                await sandbox(ukc).wait_ready(timeout=0.02)
        assert caught.value.attempts > 1

    async def test_a_probe_is_bounded_by_what_is_left_of_the_timeout(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            await sandbox(ukc).wait_ready(timeout=5)
        async with UnikraftCloud(
            token="tok", metro="fra", transport=fake.transport, timeout=2.0
        ) as ukc:
            await sandbox(ukc).wait_ready(timeout=5)
        reads = [
            call.extensions["timeout"]["read"]
            for call in fake.recorder.calls
            if call.url.path.endswith("/commands")
        ]
        # The client's unbounded read is bounded by the deadline; a shorter one stands.
        assert len(reads) == 2 and 0 < reads[0] <= 5 and reads[1] == 2.0


class TestCommands:
    async def test_run_sends_only_what_it_was_given(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            sb = sandbox(ukc)
            first = await sb.run("echo hi", cwd="/app")
            second = await sb.run("env", env={"A": "1"})
        assert body_of(fake, 0) == {"cmd": "echo hi", "cwd": "/app"}
        assert body_of(fake, 1) == {"cmd": "env", "env": {"A": "1"}}
        assert (first.uuid, second.uuid) == ("c1", "c2")

    async def test_get_reports_the_command_as_started_and_its_exit_code(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exit_code=3)
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("false", cwd="/app")
            info = await command.get()
        assert (info.cmdline, info.cwd, info.env, info.exitcode) == ("false", "/app", None, 3)

    async def test_wait_with_a_timeout_reports_a_running_command_as_none(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("sleep 1000")
            assert await command.wait(timeout=0.01) is None
            fake.commands["c1"].finish(4)
            assert await command.wait(timeout=1) == 4
            assert await command.wait() == 4
        assert body_of(fake, 1) == {"timeout_s": 0.01}
        assert fake.plugin_paths()[-2:] == ["/commands/c1/wait", "/commands/c1"]

    async def test_logs_are_decoded_and_ranged(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"hello world", stderr=b"oops")
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            whole = await command.logs()
            part = await command.logs(stdout_offset=6, stderr_offset=1, limit=3)
        assert (whole.stdout, whole.stderr) == (b"hello world", b"oops")
        assert (whole.stdout_available, whole.stderr_available) == (11, 4)
        assert (part.stdout, part.stderr) == (b"wor", b"ops")
        assert body_of(fake, 2) == {
            "stdout": {"offset": 6, "limit": 3},
            "stderr": {"offset": 1, "limit": 3},
        }

    async def test_whole_streams_come_back_verbatim(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"\x00\x01", stderr=b"\xff")
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            assert await command.stdout() == b"\x00\x01"
            assert await command.stderr() == b"\xff"

    async def test_stdin_is_fed_in_chunks_and_then_closed(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        data = bytes(range(256)) * 300  # 76800 bytes: two full chunks and a tail
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("cat")
            await command.feed_stdin(data)
        writes = fake.commands["c1"].stdin
        assert [len(chunk) for chunk, _ in writes] == [32768, 32768, 11264, 0]
        assert [eof for _, eof in writes] == [False, False, False, True]
        assert b"".join(chunk for chunk, _ in writes) == data

    async def test_stdin_takes_text_and_can_close_in_the_same_request(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("cat")
            await command.write_stdin("héllo", eof=True)
        assert fake.commands["c1"].stdin == [("héllo".encode(), True)]
        assert body_of(fake, 1) == {
            "data": base64.b64encode("héllo".encode()).decode(),
            "eof": True,
        }

    async def test_signals_go_by_number_or_name(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER, heeds_interrupt=False)
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            await command.signal(9)
            await command.signal("TERM")
        assert fake.commands["c1"].signals == [9, "TERM"]

    async def test_a_signal_that_ends_a_command_is_reported_as_minus_its_number(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            interrupted = await sandbox(ukc).run("x")
            terminated = await sandbox(ukc).run("y")
            await interrupted.signal("INT")
            await terminated.signal("SIGTERM")
            assert await interrupted.wait(timeout=5) == -2
            assert await terminated.wait(timeout=5) == -15

    async def test_a_running_command_cannot_be_deleted_but_a_finished_one_can(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            sb = sandbox(ukc)
            command = await sb.run("x")
            with pytest.raises(UnikraftCloudError) as caught:
                await command.delete()
            assert caught.value.status == 409
            fake.commands["c1"].finish(0)
            await command.delete()
            assert await sb.commands() == []

    async def test_forgetting_logs_makes_them_gone(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"x")
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            await command.delete_logs()
            with pytest.raises(UnikraftCloudError) as caught:
                await command.logs()
        assert caught.value.status == 410

    async def test_commands_are_listed_and_reattached_by_uuid(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            sb = sandbox(ukc)
            await sb.run("a")
            await sb.run("b")
            listed = await sb.commands()
            again = sb.command("c2")
            info = await again.get()
        assert [c.uuid for c in listed] == ["c1", "c2"]
        assert info.cmdline == "b"


class TestStreaming:
    async def test_yields_output_as_it_arrives_then_drains_after_the_end(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sandbox_module, "LOG_CHUNK_SIZE", 4)
        fake = FakeSandbox()
        fake.on_run(stdout=b"abcdefgh", stderr=b"E", exits_after_polls=1)
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            chunks = [chunk async for chunk in command.stream()]
        assert chunks == [
            OutputChunk("stdout", b"abcd"),
            OutputChunk("stderr", b"E"),
            OutputChunk("stdout", b"efgh"),
        ]

    async def test_waits_for_the_end_alongside_the_polling(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"hi", exits_after_polls=2)
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            chunks = [chunk async for chunk in command.stream()]
        assert b"".join(c.data for c in chunks) == b"hi"
        paths = fake.plugin_paths()
        assert "/commands/c1/wait" in paths
        assert "/commands/c1/wait_timeout" not in paths

    async def test_gives_up_after_three_failed_polls_in_a_row(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        fake.failing_polls = 3
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            with pytest.raises(UnikraftCloudError) as caught:
                [chunk async for chunk in command.stream()]
        assert caught.value.status == 500

    async def test_recovers_from_fewer_failed_polls(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"ok", exits_after_polls=1)
        fake.failing_polls = 2
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            chunks = [chunk async for chunk in command.stream()]
        assert chunks == [OutputChunk("stdout", b"ok")]


class TestExec:
    async def test_collects_the_output_and_exit_code_without_deleting(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"out", stderr=b"err", exit_code=2, exits_after_polls=1)
        async with cloud(fake) as ukc:
            result = await sandbox(ukc).exec("make", cwd="/app", env={"CI": "1"})
        assert (result.uuid, result.exit_code, result.stdout, result.stderr) == (
            "c1",
            2,
            b"out",
            b"err",
        )
        assert result.interrupted is False
        assert "c1" in fake.commands
        assert fake.recorder.calls[0].method == "POST"
        assert body_of(fake, 0) == {"cmd": "make", "cwd": "/app", "env": {"CI": "1"}}
        assert all(c.method != "DELETE" for c in fake.recorder.calls)

    async def test_feeds_stdin_while_the_command_runs(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"echoed", exits_after_polls=2)
        async with cloud(fake) as ukc:
            result = await sandbox(ukc).exec("cat", stdin="input")
        assert result.stdout == b"echoed"
        assert fake.commands["c1"].stdin == [(b"input", False), (b"", True)]

    async def test_a_timeout_interrupts_and_then_waits_for_the_end(self) -> None:
        fake = FakeSandbox()
        fake.on_run(stdout=b"partial", exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            result = await sandbox(ukc).exec("sleep 1000", timeout=0.02)
        assert fake.commands["c1"].signals == [2]
        assert (result.exit_code, result.interrupted, result.stdout) == (-2, True, b"partial")

    async def test_a_command_that_ignores_the_interrupt_is_given_up_on(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER, heeds_interrupt=False)
        async with cloud(fake) as ukc:
            with pytest.raises(ExecTimeoutError) as caught:
                await sandbox(ukc).exec("trap '' INT; sleep 1000", timeout=0.02, wait_delay=0.02)
        assert caught.value.command.uuid == "c1"
        assert isinstance(caught.value, TimeoutError)
        assert fake.commands["c1"].signals == [2]
        assert fake.commands["c1"].running

    async def test_without_a_grace_period_it_waits_for_a_stubborn_command(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=6, exit_code=1, heeds_interrupt=False)
        async with cloud(fake) as ukc:
            result = await sandbox(ukc).exec("x", timeout=0.001)
        assert (result.exit_code, result.interrupted) == (1, True)

    async def test_a_feed_that_fails_ends_the_exec_rather_than_the_command(self) -> None:
        fake = FakeSandbox()
        fake.failing_stdin = 1
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            with pytest.raises(UnikraftCloudError) as caught:
                await sandbox(ukc).exec("cat", stdin=b"never arrives", timeout=5)
        assert caught.value.status == 502
        # The command waits for input that will not come; it is the caller's now.
        assert fake.commands["c1"].running
        assert fake.commands["c1"].stdin == []
        assert fake.commands["c1"].signals == []

    async def test_an_unencodable_input_is_refused_before_the_command_starts(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            with pytest.raises(UnicodeEncodeError):
                await sandbox(ukc).exec("cat", stdin="lone \udc80 surrogate")
        assert fake.commands == {}

    async def test_the_final_read_of_the_exit_code_is_retried(self) -> None:
        fake = FakeSandbox()
        fake.failing_reads = 1
        fake.on_run(stdout=b"out", exit_code=3, exits_after_polls=1)
        async with cloud(fake) as ukc:
            result = await sandbox(ukc).exec("x")
        assert (result.exit_code, result.stdout) == (3, b"out")
        assert fake.plugin_paths().count("/commands/c1") == 2

    async def test_a_command_that_ends_before_its_input_arrives_reports_its_exit_code(
        self,
    ) -> None:
        fake = FakeSandbox()
        fake.on_run(exit_code=127, exits_after_polls=0)
        async with cloud(fake) as ukc:
            result = await sandbox(ukc).exec("nosuchcmd", stdin=b"never read")
        # The plugin refused the input of an ended command; the exit code is the story.
        assert (result.exit_code, result.interrupted) == (127, False)
        assert fake.commands["c1"].stdin == []


class TestFiles:
    async def test_mkdir_with_and_without_parents(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            fs = sandbox(ukc).fs
            await fs.mkdir("/app/x")
            await fs.mkdir("/app/y/z", parents=True)
        assert fake.dirs == [("/app/x", False), ("/app/y/z", True)]

    async def test_bytes_are_written_as_base64_and_text_as_utf8(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            fs = sandbox(ukc).fs
            await fs.write("/app/blob", b"\x00\xff")
            await fs.write("/app/note", "héllo")
        assert body_of(fake, 0)["encoding"] == "base64"
        assert body_of(fake, 1)["encoding"] == "utf-8"
        assert fake.files == {"/app/blob": b"\x00\xff", "/app/note": "héllo".encode()}

    async def test_append_adds_to_a_file(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            fs = sandbox(ukc).fs
            await fs.write("/app/log", "a")
            await fs.write("/app/log", "b", append=True)
        assert fake.files["/app/log"] == b"ab"

    async def test_read_returns_bytes_and_read_text_decodes(self) -> None:
        fake = FakeSandbox()
        fake.files["/app/f"] = "héllo".encode()
        async with cloud(fake) as ukc:
            fs = sandbox(ukc).fs
            assert await fs.read("/app/f") == "héllo".encode()
            assert await fs.read_text("/app/f") == "héllo"
        assert fake.plugin_paths() == ["/fs/read_raw", "/fs/read_raw"]

    async def test_a_missing_file_is_not_found(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            with pytest.raises(NotFoundError):
                await sandbox(ukc).fs.read("/nope")

    async def test_upload_lands_in_a_directory_named_either_way(self) -> None:
        fake = FakeSandbox()
        fake.dirs.append(("/app", False))
        async with cloud(fake) as ukc:
            fs = sandbox(ukc).fs
            assert await fs.upload("/app/", "a.bin", b"1") == "/app/a.bin"
            # Without its slash, the plugin's refusal says the path is a directory.
            assert await fs.upload("/app", "b.bin", b"2") == "/app/b.bin"
            assert await fs.upload("/deep/c.txt", "ignored", "3", parents=True) == "/deep/c.txt"
            # A file that is there is replaced, as the CLI's upload has it.
            assert await fs.upload("/app/a.bin", "ignored", b"9") == "/app/a.bin"
        assert fake.files == {"/app/a.bin": b"9", "/app/b.bin": b"2", "/deep/c.txt": b"3"}
        assert ("/deep", True) in fake.dirs
        ops = [c.url.path.rsplit("/", 1)[1] for c in fake.recorder.calls if "/fs/" in c.url.path]
        assert ops == ["write", "write", "write", "mkdir", "write", "write"]

    async def test_upload_wants_a_filename_that_is_one_segment(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            with pytest.raises(ValueError, match="one path segment"):
                await sandbox(ukc).fs.upload("/app/", "", b"1")
            with pytest.raises(ValueError, match="one path segment"):
                await sandbox(ukc).fs.upload("/app", "a/b", b"1")
        assert fake.plugin_paths() == []


class SlowReads(FakeSandbox):
    """A platform whose instance reads take a moment."""

    def __init__(self, delay: float) -> None:
        super().__init__()
        self.delay = delay
        self.reads = 0

    async def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/instances" and request.method == "GET":
            self.reads += 1
            await asyncio.sleep(self.delay)
        return await super().handle(request)


class LateInstance(FakeSandbox):
    """A platform that lists the instance only from the given read on."""

    def __init__(self, listed_from: int) -> None:
        super().__init__()
        self.listed_from = listed_from
        self.reads = 0

    async def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/instances" and request.method == "GET":
            self.reads += 1
            if self.reads < self.listed_from:
                return httpx.Response(200, json=envelope({"instances": []}))
        return await super().handle(request)


class TestResolvingAgain:
    async def test_a_lookup_the_caller_gave_up_on_still_serves_the_next_call(self) -> None:
        fake = SlowReads(delay=0.05)
        async with cloud(fake) as ukc:
            sb = ukc.instances.get(name="web").sandbox()
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(sb.ready(), 0.001)
            # The lookup went on without its first caller; nobody is poisoned.
            assert await sb.ready() is True
            assert (await sb.exec("x")).exit_code == 0
        assert fake.reads == 1

    async def test_wait_ready_waits_for_an_instance_not_listed_yet(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(sandbox_module, "_sleep", fake_sleep)
        fake = LateInstance(listed_from=3)
        async with cloud(fake) as ukc:
            sb = ukc.instances.get(name="web").sandbox()
            await sb.wait_ready(timeout=60)
            assert await sb.ready() is True
        assert fake.reads == 3
        assert fake.plugin_paths() == ["/commands"] * 2

    async def test_wait_ready_searches_every_metro_again_for_an_instance_not_listed_yet(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(sandbox_module, "_sleep", fake_sleep)
        fake = LateInstance(listed_from=3)
        async with UnikraftCloud(token="tok", transport=fake.transport) as ukc:
            # Account-wide, the name is searched for in every metro; a search
            # that found nothing is made again rather than kept as the answer.
            sb = ukc.instances.get(name="web").sandbox()
            await sb.wait_ready(timeout=60)
        assert fake.reads >= 3
        assert fake.plugin_paths() == ["/commands"]

    async def test_an_instance_never_listed_is_a_plugin_not_ready(self) -> None:
        fake = LateInstance(listed_from=NEVER)
        async with cloud(fake) as ukc:
            sb = ukc.instances.get(name="web").sandbox()
            with pytest.raises(PluginNotReadyError) as caught:
                await sb.wait_ready(timeout=0)
        assert isinstance(caught.value.__cause__, NotFoundError)
        assert isinstance(caught.value, UnikraftCloudError)

    async def test_wait_ready_sleeps_no_longer_than_the_deadline_allows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slept: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(sandbox_module, "_sleep", fake_sleep)
        fake = FakeSandbox()
        fake.unready = 1
        async with cloud(fake) as ukc:
            await sandbox(ukc).wait_ready(timeout=0.1)
        # The first interval would be a quarter second; the deadline is nearer.
        assert len(slept) == 1 and 0.09 < slept[0] <= 0.1


class RefusedCreate(FakeSandbox):
    """A platform that refuses to create the instance a plugin would run in."""

    def _platform_instances(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(400, json={"status": "error", "message": "no such image"})
        return super()._platform_instances(request)


class ForbiddenLookups(FakeSandbox):
    """A platform whose every metro refuses the token for an instance lookup."""

    def _platform_instances(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(403, json={"status": "error", "message": "forbidden"})
        return super()._platform_instances(request)


class TestFailuresThatCannotChange:
    async def test_wait_ready_raises_a_create_that_failed_at_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(sandbox_module, "_sleep", fake_sleep)
        fake = RefusedCreate()
        async with cloud(fake) as ukc:
            sb = ukc.instances.create(image="org/missing:v1").sandbox()
            with pytest.raises(UnikraftCloudError) as caught:
                await sb.wait_ready(timeout=60)
            assert await sb.ready() is False
        # The handle keeps the create's one outcome, so probing again would
        # only raise the same failure again: it is raised as it is, not as a
        # plugin not ready, and the create is not sent again.
        assert caught.value.status == 400
        assert not isinstance(caught.value, PluginNotReadyError)
        assert [call.method for call in fake.recorder.calls] == ["POST"]

    async def test_a_token_every_metro_refuses_is_raised_at_once(self) -> None:
        fake = ForbiddenLookups()
        async with UnikraftCloud(token="tok", transport=fake.transport) as ukc:
            sb = ukc.instances.get(name="web").sandbox()
            with pytest.raises(MetroFanoutError) as caught:
                await sb.wait_ready(timeout=60)
            assert caught.value.status == 403
            with pytest.raises(MetroFanoutError):
                await sb.ready()
        # One round of lookups per call: nothing was waited out.
        assert len(fake.recorder.metros("/v1/instances")) == 4


class ExitedBeforeSignal(FakeSandbox):
    """A plugin whose command exits just as it is signalled, so the signal is refused."""

    async def _command(
        self, request: httpx.Request, command: FakeCommand, op: str, body: dict[str, Any]
    ) -> httpx.Response:
        if op == "signal":
            command.finish(3)
            return httpx.Response(409, json={"status": "error", "message": "process has exited"})
        return await super()._command(request, command, op, body)


class TestTimeoutsThatCannotInterrupt:
    async def test_a_lost_interrupt_raises_rather_than_waiting_for_nothing(self) -> None:
        fake = FakeSandbox()
        fake.failing_signals = 1
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            with pytest.raises(ExecTimeoutError) as caught:
                await sandbox(ukc).exec("x", timeout=0.01)
            assert isinstance(caught.value, UnikraftCloudError)
            assert caught.value.command.uuid == "c1"
            # Why the interrupt was lost travels along.
            assert isinstance(caught.value.__cause__, UnikraftCloudError)
            assert caught.value.__cause__.status == 500
        assert fake.commands["c1"].running

    async def test_a_command_that_exited_as_it_was_interrupted_reports_its_end(self) -> None:
        fake = ExitedBeforeSignal()
        fake.on_run(stdout=b"all of it", exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            result = await sandbox(ukc).exec("x", timeout=0.01)
        assert (result.exit_code, result.interrupted, result.stdout) == (3, True, b"all of it")

    async def test_a_negative_timeout_or_grace_is_refused(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            with pytest.raises(ValueError, match="timeout"):
                await sandbox(ukc).exec("x", timeout=-1)
            with pytest.raises(ValueError, match="wait_delay"):
                await sandbox(ukc).exec("x", timeout=1, wait_delay=-1)
        assert fake.commands == {}

    async def test_a_grace_period_needs_a_timeout(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            with pytest.raises(TypeError, match="timeout"):
                await sandbox(ukc).exec("x", wait_delay=1)
        assert fake.commands == {}

    async def test_a_cancelled_exec_leaves_the_command_running_unsignalled(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            running = asyncio.ensure_future(sandbox(ukc).exec("x"))
            await asyncio.sleep(0.01)
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
        assert fake.commands["c1"].running
        assert fake.commands["c1"].signals == []


class TestCommandShapes:
    async def test_an_argument_vector_runs_without_a_shell(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            await sandbox(ukc).run(["echo", "hi there"])
            await sandbox(ukc).exec(("printf", "%s", "a b"), cwd="/app")
        assert body_of(fake, 0) == {"cmd": ["echo", "hi there"]}
        assert body_of(fake, 1) == {"cmd": ["printf", "%s", "a b"], "cwd": "/app"}

    async def test_deleting_a_running_command_says_it_still_runs(self) -> None:
        fake = FakeSandbox()
        fake.on_run(exits_after_polls=NEVER)
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            with pytest.raises(UnikraftCloudError, match="still running") as caught:
                await command.delete()
        assert caught.value.status == 409
        assert not isinstance(caught.value, AlreadyExistsError)
        assert isinstance(caught.value.__cause__, UnikraftCloudError)

    async def test_the_sandbox_errors_are_the_sdks_and_timeouts_both(self) -> None:
        assert issubclass(PluginNotReadyError, UnikraftCloudError)
        assert issubclass(PluginNotReadyError, TimeoutError)
        assert issubclass(ExecTimeoutError, UnikraftCloudError)
        assert issubclass(ExecTimeoutError, TimeoutError)

    async def test_a_negative_wait_is_refused_before_it_is_sent(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            command = await sandbox(ukc).run("x")
            with pytest.raises(ValueError, match="zero or more"):
                await command.wait(timeout=-1)
        assert "/commands/c1/wait_timeout" not in fake.plugin_paths()
