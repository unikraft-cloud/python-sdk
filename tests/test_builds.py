# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The build client: what a build request carries, how the service's refusals
# read, and how the progress stream is followed across cuts and replays.

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from unikraft_cloud import (
    NotFoundError,
    ServerError,
    UnikraftCloud,
    UnikraftCloudError,
    git_source,
    image_output,
    kraftfile_from,
)
from unikraft_cloud.api.build import models
from unikraft_cloud.resources import builds as builds_module

from .conftest import Recorder, queued

BUILD_URL = "https://b.example.com"
ID = "0b9c6f1e-6a52-4d1f-9a43-2f0d9b7f5c11"

LINE_KERNEL = '{"vertexes":[null,{"digest":"sha256:1","name":"[kernel] pull"}]}'
LINE_ROOTFS = '{"vertexes":[{"digest":"sha256:2","name":"[rootfs 1/1] RUN npm ci"}]}'
LINE_LOG = (
    '{"logs":[{"vertex":"sha256:2","stream":2,"data":"aGk=","timestamp":"2026-10-20T12:00:00Z"}]}'
)
LINE_WARNING = '{"warnings":[{"vertex":"sha256:2","level":1,"detail":[null,"ZGV0YWls"]}]}'
LINE_RESULT = (
    '{"result":{"images":[{"ref":"index.unikraft.io/acme/app:1","digest":"sha256:4c1a",'
    '"platforms":["linux/amd64"]}]}}'
)
LINE_ERROR = '{"error":{"code":"interrupted","message":"the service restarted"}}'

SRC = git_source("https://github.com/acme/app.git", "main", subdir="app")
UNAVAILABLE = (503, {"error": {"code": "internal", "message": "shutting down"}})


def client(recorder: Recorder) -> UnikraftCloud:
    return UnikraftCloud(token="tok", transport=recorder.transport, build_url=BUILD_URL)


def build(status: str = "running") -> dict[str, Any]:
    return {
        "id": ID,
        "status": status,
        "builder": "default",
        "created_at": "2026-10-20T12:00:00Z",
    }


def spec(**overrides: Any) -> dict[str, Any]:
    """The properties of a build of the example app, as `create` takes them."""
    return {
        "kraftfile": kraftfile_from(SRC),
        "contexts": {"context": SRC},
        "output": [image_output("index.unikraft.io/acme/app:1.2.3")],
        **overrides,
    }


@dataclass
class Stream:
    """One answer to a request for the progress stream: its lines, cut short or not."""

    lines: Sequence[str]
    cut: bool = False
    media: str = "application/x-ndjson"
    status: int = 200
    chunks: list[bytes] = field(init=False)
    closed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.chunks = [f"{line}\n".encode() for line in self.lines]


class _Body(httpx.AsyncByteStream):
    def __init__(self, answer: Stream) -> None:
        self.answer = answer

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.answer.chunks:
            yield chunk
        if self.answer.cut:
            raise httpx.ReadError("connection reset mid-body")

    async def aclose(self) -> None:
        self.answer.closed = True


def progress(answers: Sequence[Any]) -> Recorder:
    """A transport answering each request in turn: a stream, a (status, body) pair, or an error.

    A request past the last answer fails the test, so a follower that asks once
    too often is caught rather than left looping while the waits cost nothing.
    """
    remaining = list(answers)

    def handler(request: httpx.Request) -> httpx.Response:
        assert remaining, "the progress stream was asked for once too often"
        answer = remaining.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, tuple):
            return httpx.Response(answer[0], json=answer[1])
        return httpx.Response(
            answer.status, stream=_Body(answer), headers={"content-type": answer.media}
        )

    return Recorder(handler)


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The waits between attempts, recorded instead of slept."""
    waited: list[float] = []

    async def record(seconds: float) -> None:
        waited.append(seconds)

    monkeypatch.setattr(builds_module, "_sleep", record)
    return waited


async def events(ukc: UnikraftCloud) -> list[models.BuildEvent]:
    async with contextlib.aclosing(ukc.builds.logs(ID)) as logs:
        return [event async for event in logs]


class TestBuilds:
    async def test_create_sends_the_request_and_returns_the_build(self) -> None:
        recorder = queued([(201, build())])
        async with client(recorder) as ukc:
            created = await ukc.builds.create(**spec())

        sent = recorder.calls[0]
        assert (sent.method, str(sent.url)) == ("POST", f"{BUILD_URL}/v1/builds")
        # Only what was given goes on the wire: no nulls for the fields left out.
        assert json.loads(sent.content) == {
            "kraftfile": {"git": "https://github.com/acme/app.git", "ref": "main", "subdir": "app"},
            "contexts": {
                "context": {
                    "git": "https://github.com/acme/app.git",
                    "ref": "main",
                    "subdir": "app",
                }
            },
            "output": [{"image": "index.unikraft.io/acme/app:1.2.3"}],
        }
        assert (created.id, created.status) == (ID, "running")

    async def test_create_refuses_a_property_the_api_does_not_describe(self) -> None:
        recorder = queued([(201, build())])
        async with client(recorder) as ukc:
            with pytest.raises(TypeError, match="'kraftfil' is not one of the properties"):
                await ukc.builds.create(**spec(kraftfil="runtime: nginx\n"))
        assert recorder.calls == []

    async def test_an_inline_kraftfile_goes_as_given(self) -> None:
        recorder = queued([(201, build()), (201, build())])
        async with client(recorder) as ukc:
            await ukc.builds.create(**spec(kraftfile="spec: v0.6\nruntime: nginx\n"))
            await ukc.builds.create(**spec(kraftfile={"spec": "v0.6", "runtime": "nginx"}))
        assert json.loads(recorder.calls[0].content)["kraftfile"] == "spec: v0.6\nruntime: nginx\n"
        assert json.loads(recorder.calls[1].content)["kraftfile"] == {
            "spec": "v0.6",
            "runtime": "nginx",
        }

    async def test_the_build_url_falls_back_to_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UKC_BUILD_SERVER", "https://staging.example.com/v1")
        # No builds is a null, the service's nil slice, as well as an empty list.
        recorder = queued([(200, {"builds": None})])
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            assert await ukc.builds.list() == []
            await ukc.api.build.builds.list_builds()
            await ukc.metro("fra").api.build.builds.list_builds()
        assert recorder.urls == ["https://staging.example.com/v1/builds"] * 3

    async def test_an_argument_beats_the_environment_and_the_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UKC_BUILD_SERVER", "https://staging.example.com")
        recorder = queued([(200, {"builds": []})])
        async with client(recorder) as ukc:
            await ukc.builds.list()
        monkeypatch.delenv("UKC_BUILD_SERVER")
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            await ukc.builds.list()
        assert recorder.urls == [f"{BUILD_URL}/v1/builds", "https://build.unikraft.cloud/v1/builds"]

    async def test_the_build_url_must_be_a_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A bare host is not a metro code to expand, as the platform's would be.
        with pytest.raises(ValueError, match="build_url must be an http"):
            UnikraftCloud(token="tok", build_url="build.staging.example.com")
        monkeypatch.setenv("UKC_BUILD_SERVER", "localhost:8080")
        with pytest.raises(ValueError, match="'localhost:8080'"):
            UnikraftCloud(token="tok")

    async def test_a_refusal_carries_the_services_message_and_code(self) -> None:
        recorder = queued(
            [(400, {"error": {"code": "unsupported", "message": "unsupported field: builder"}})]
        )
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError) as refused:
                await ukc.builds.create(**spec())

        assert str(refused.value) == "unsupported field: builder"
        assert refused.value.errors is not None
        assert refused.value.errors[0].code == "unsupported"

    async def test_a_missing_build_is_not_known_to_be_absent(self) -> None:
        # The service says `not_found` for a route that is not there too, so
        # a 404 cannot vouch that the build is absent.
        recorder = queued([(404, {"error": {"code": "not_found", "message": f"no build {ID}"}})])
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError) as missing:
                await ukc.builds.get(ID)
        assert missing.value.absent is False

    async def test_the_operations_take_the_builds_id(self) -> None:
        recorder = queued(
            [(200, {"builds": [build()]}), (202, build()), (200, build("cancelled")), (204, None)]
        )
        async with client(recorder) as ukc:
            [found] = await ukc.builds.list(status="running", limit=1)
            await found.cancel()
            refreshed = await found.refresh()
            await refreshed.delete()

        assert refreshed.status == "cancelled"
        assert recorder.urls[0] == f"{BUILD_URL}/v1/builds?status=running&limit=1"
        assert [(c.method, c.url.path) for c in recorder.calls[1:]] == [
            ("POST", f"/v1/builds/{ID}/cancel"),
            ("GET", f"/v1/builds/{ID}"),
            ("DELETE", f"/v1/builds/{ID}"),
        ]

    async def test_an_id_that_is_not_one_path_segment_is_refused_before_sending(self) -> None:
        recorder = queued([(200, {"builds": [{"status": "running"}]})])
        async with client(recorder) as ukc:
            [unnamed] = await ukc.builds.list()
            with pytest.raises(ValueError, match="no ID"):
                await unnamed.refresh()
            for bad in ("", ".", "..", f"{ID}/logs"):
                for op in (ukc.builds.get, ukc.builds.cancel, ukc.builds.delete):
                    with pytest.raises(ValueError, match="one segment of a path"):
                        await op(bad)
                for follow in (ukc.builds.logs, ukc.builds.plain_logs):
                    with pytest.raises(ValueError, match="one segment of a path"):
                        await anext(follow(bad))
        assert len(recorder.calls) == 1


class TestLogs:
    async def test_yields_every_event_once_and_stops_at_the_last(self) -> None:
        recorder = progress(
            [Stream([LINE_KERNEL, "", LINE_LOG, LINE_WARNING, LINE_RESULT, LINE_ROOTFS])]
        )
        async with client(recorder) as ukc:
            got = await events(ukc)

        assert recorder.calls[0].headers["accept"] == "application/x-ndjson"
        assert recorder.paths == [f"/v1/builds/{ID}/logs"]
        # Four events: the empty line is not one, and nothing follows the last.
        assert len(got) == 4
        # buildkit's nulls are dropped rather than refused, however deep.
        assert got[2].warnings is not None and got[2].warnings[0].detail == ["ZGV0YWls"]

    async def test_a_cut_stream_is_asked_again_and_the_replay_skipped(
        self, sleeps: list[float]
    ) -> None:
        cut_mid_line = Stream([LINE_KERNEL, LINE_ROOTFS, LINE_LOG])
        cut_mid_line.chunks.append(b'{"vertexes":[{"dig')
        recorder = progress(
            [
                Stream([LINE_KERNEL, LINE_ROOTFS], cut=True),
                # The replay has it all, plus a line cut mid-way through.
                cut_mid_line,
                Stream([LINE_KERNEL, LINE_ROOTFS, LINE_LOG, LINE_RESULT]),
            ]
        )
        async with client(recorder) as ukc:
            got = await events(ukc)

        assert [bool(e.vertexes) for e in got] == [True, True, False, False]
        # A wait before each replay, at the shortest: every attempt brought an event.
        assert sleeps == [0.25, 0.25]

    async def test_a_shorter_replay_that_ends_in_an_error_is_not_skipped(
        self, sleeps: list[float]
    ) -> None:
        recorder = progress(
            [
                Stream([LINE_KERNEL, LINE_ROOTFS, LINE_LOG]),
                Stream([LINE_ERROR]),
            ]
        )
        async with client(recorder) as ukc:
            got = await events(ukc)

        assert len(got) == 4
        assert got[3].error is not None and got[3].error.code == "interrupted"

    async def test_the_wait_between_idle_replays_grows_to_a_cap(self, sleeps: list[float]) -> None:
        recorder = progress([Stream([LINE_KERNEL])] * 8 + [Stream([LINE_KERNEL, LINE_RESULT])])
        async with client(recorder) as ukc:
            await events(ukc)

        assert sleeps == [0.25, 0.5, 1.0, 2.0, 4.0, 5.0, 5.0, 5.0]

    async def test_a_service_that_cannot_answer_is_given_up_on(self, sleeps: list[float]) -> None:
        recorder = progress([UNAVAILABLE] * 6)
        async with client(recorder) as ukc:
            with pytest.raises(ServerError) as given_up:
                await events(ukc)

        assert "shutting down" in str(given_up.value)
        assert isinstance(given_up.value.__cause__, ServerError)
        assert sleeps == [0.25, 0.5, 1.0, 2.0, 4.0]

    async def test_the_budget_is_for_attempts_in_a_row(self, sleeps: list[float]) -> None:
        recorder = progress(
            [
                # A 5xx whose body broke off is as much an answer the service could not give,
                # and a service that answered before and cannot be reached now is asked again.
                Stream([], cut=True, status=503, media="application/json"),
                httpx.ConnectError("connection refused"),
                *[UNAVAILABLE] * 3,
                # A stream, cut, starts the count over.
                Stream([LINE_KERNEL], cut=True),
                *[UNAVAILABLE] * 5,
                Stream([LINE_KERNEL, LINE_ROOTFS, LINE_RESULT]),
            ]
        )
        async with client(recorder) as ukc:
            await events(ukc)

    async def test_not_reaching_a_service_that_answered_spends_the_budget(
        self, sleeps: list[float]
    ) -> None:
        unreachable = httpx.ConnectError("connection refused")
        recorder = progress([Stream([LINE_KERNEL], cut=True), *[unreachable] * 6])
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError) as given_up:
                await events(ukc)
        assert given_up.value.kind == "network"
        assert len(recorder.calls) == 7

    async def test_a_service_that_never_answered_is_raised_at_once(self) -> None:
        recorder = progress([httpx.ConnectError("connection refused")])
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError) as unreachable:
                await events(ukc)
        assert unreachable.value.kind == "network"

    async def test_a_refusal_is_raised_at_once(self) -> None:
        recorder = progress([(404, {"error": {"code": "not_found", "message": f"no build {ID}"}})])
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError):
                await events(ukc)

    async def test_a_refusal_that_broke_off_is_raised_at_once(self, sleeps: list[float]) -> None:
        # A refusal whose body was cut is still a refusal, not a stream cut
        # short: even once the service has answered, it is not asked again.
        recorder = progress(
            [
                Stream([LINE_KERNEL], cut=True),
                Stream([], cut=True, status=404, media="application/json"),
            ]
        )
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError):
                await events(ukc)

    async def test_a_closed_client_is_not_asked_again(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorder = progress([Stream([LINE_KERNEL], cut=True)])
        ukc = client(recorder)
        # The wait before the replay closes the client, as a shutdown would.
        monkeypatch.setattr(builds_module, "_sleep", lambda _: ukc.aclose())
        with pytest.raises(UnikraftCloudError, match=r"^This client is closed"):
            await events(ukc)

    async def test_an_answer_that_is_not_a_stream_is_raised_at_once(self) -> None:
        recorder = progress([(200, {"builds": []})])
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError) as wrong:
                await events(ukc)
        assert wrong.value.kind == "parse"
        assert "got application/json" in str(wrong.value)

    async def test_a_line_that_does_not_parse_is_a_parse_error(self) -> None:
        recorder = progress([Stream([LINE_KERNEL, '{"vertexes": "not a list"}'])])
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError) as bad:
                await events(ukc)
        assert bad.value.kind == "parse"
        assert "Line 2" in str(bad.value)

    async def test_closing_early_releases_the_connection(self) -> None:
        answer = Stream([LINE_KERNEL, LINE_ROOTFS, LINE_LOG])
        recorder = progress([answer])
        async with client(recorder) as ukc:
            logs = ukc.builds.logs(ID, timeout=1.5)
            async for _ in logs:
                break
            await logs.aclose()
        assert answer.closed is True
        assert recorder.calls[0].extensions["timeout"]["read"] == 1.5


class TestPlainLogs:
    async def test_yields_the_text_as_it_arrives(self) -> None:
        answer = Stream([], media="text/plain; charset=utf-8")
        # A character split across two chunks still comes out whole.
        answer.chunks = [b"#1 [kernel] pull\n#1 DONE 0.3s \xe2", b"\x9c\x93\n"]
        recorder = progress([answer])
        async with (
            client(recorder) as ukc,
            contextlib.aclosing(ukc.builds.plain_logs(ID, timeout=1.5)) as lines,
        ):
            got = [text async for text in lines]

        assert recorder.calls[0].headers["accept"] == "text/plain"
        assert recorder.calls[0].extensions["timeout"]["read"] == 1.5
        assert "".join(got) == "#1 [kernel] pull\n#1 DONE 0.3s ✓\n"

    async def test_a_cut_is_raised_and_not_asked_again(self) -> None:
        recorder = progress([Stream(["#1 [kernel] pull"], cut=True, media="text/plain")])
        got: list[str] = []
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError):
                async with contextlib.aclosing(ukc.builds.plain_logs(ID)) as lines:
                    async for text in lines:
                        got.append(text)

        assert got == ["#1 [kernel] pull\n"]
