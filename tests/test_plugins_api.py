# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The plugin plumbing: the instance route a plugin hangs off, and the generated
# sandbox clients on top of it.

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from unikraft_cloud import (
    ApiClientConfig,
    NotFoundError,
    RawResponse,
    UnikraftCloud,
    UnikraftCloudError,
)
from unikraft_cloud.api.plugins import PluginsApi, plugin_base_url
from unikraft_cloud.api.plugins.sandbox import SandboxApi, models

from .conftest import Recorder, envelope, queued

ROUTE = "https://api.fra.unikraft.cloud/v1/instances/u1/plugins/sandbox"


def cloud(recorder: Recorder, **config: Any) -> UnikraftCloud:
    return UnikraftCloud(token="tok", transport=recorder.transport, **config)


def blob(status: int, body: bytes, **headers: str) -> Recorder:
    """A transport answering one raw-bytes payload."""
    return Recorder(
        lambda request: httpx.Response(
            status, content=body, headers={"content-type": "application/octet-stream", **headers}
        )
    )


class TestPluginRoute:
    def test_hangs_off_the_instance_on_its_metro(self) -> None:
        assert plugin_base_url("https://api.fra.unikraft.cloud/", "u1", "sandbox") == ROUTE

    def test_encodes_each_segment_as_one_segment(self) -> None:
        url = plugin_base_url("https://api.fra.unikraft.cloud", "a/b", "my plugin")
        assert url.endswith("/v1/instances/a%2Fb/plugins/my%20plugin")

    def test_a_base_url_carrying_v1_is_not_doubled(self) -> None:
        # The control plane reports a metro endpoint with its /v1; so does UKC_METRO.
        assert plugin_base_url("https://api.fra.unikraft.cloud/v1", "u1", "sandbox") == ROUTE
        assert plugin_base_url("https://api.fra.unikraft.cloud/v1/", "u1", "sandbox") == ROUTE

    async def test_a_plugin_named_v1_keeps_its_route(self) -> None:
        route = plugin_base_url("https://api.fra.unikraft.cloud/v1", "u1", "v1")
        assert route == ROUTE.replace("/sandbox", "/v1")
        recorder = queued([(200, envelope({"commands": []}))])
        config = ApiClientConfig(base_url=route, token="tok", transport=recorder.transport)
        async with SandboxApi(config) as raw:
            await raw.commands.list_commands()
        assert recorder.urls == [route + "/commands"]


class TestSandboxPlumbing:
    async def test_for_instance_targets_the_plugin_route(self) -> None:
        recorder = queued([(200, envelope({"commands": ["c1"]}))])
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            res = await raw.commands.list_commands()
        assert recorder.urls == [ROUTE + "/commands"]
        assert recorder.calls[0].headers["authorization"] == "Bearer tok"
        assert res.data is not None and res.data.commands == ["c1"]

    async def test_a_scoped_metro_pins_the_route(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))])
        async with cloud(recorder) as ukc:
            raw = ukc.metro("dal").api.plugins.sandbox.for_instance("u1")
            await raw.commands.list_commands()
        assert recorder.calls[0].url.host == "api.dal.unikraft.cloud"

    async def test_the_plugin_name_and_metro_can_be_named_per_instance(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))])
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance(
                "u1", plugin="sb2", base_url="https://api.dal.unikraft.cloud"
            )
            await raw.commands.list_commands()
        assert recorder.urls == [
            "https://api.dal.unikraft.cloud/v1/instances/u1/plugins/sb2/commands"
        ]

    async def test_run_command_sends_only_the_fields_given(self) -> None:
        recorder = queued([(200, envelope({"uuid": "c1"}))])
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            res = await raw.commands.run_command(
                body=models.RunCommandRequest(cmd="echo hi", cwd="/app")
            )
        request = recorder.calls[0]
        assert (request.method, request.url.path) == (
            "POST",
            "/v1/instances/u1/plugins/sandbox/commands",
        )
        assert json.loads(request.content) == {"cmd": "echo hi", "cwd": "/app"}
        assert res.data is not None and res.data.uuid == "c1"

    async def test_the_envelope_is_parsed_into_the_generated_models(self) -> None:
        command = {"uuid": "c1", "cmdline": "echo hi", "cwd": None, "env": None, "exitcode": None}
        recorder = queued([(200, envelope(command))])
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            res = await raw.commands.get_command_by_uuid("c1")
        assert recorder.urls == [ROUTE + "/commands/c1"]
        assert res.data is not None
        assert (res.data.cmdline, res.data.exitcode) == ("echo hi", None)

    async def test_a_raw_log_carries_the_range_header_and_returns_bytes(self) -> None:
        recorder = blob(206, b"ello", **{"content-range": "bytes 1-4/5"})
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            out = await raw.commands.get_raw_command_log("c1", "stdout", range="bytes=1-4")
        request = recorder.calls[0]
        assert request.url.path == "/v1/instances/u1/plugins/sandbox/commands/c1/logs/raw/stdout"
        assert request.headers["range"] == "bytes=1-4"
        assert request.headers["accept"] == "application/octet-stream"
        assert isinstance(out, RawResponse)
        assert (out.status, out.content, out.content_range) == (206, b"ello", "bytes 1-4/5")

    async def test_a_raw_log_without_a_range_sends_no_range_header(self) -> None:
        recorder = blob(200, b"hello")
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            out = await raw.commands.get_raw_command_log("c1", "stderr")
        assert "range" not in recorder.calls[0].headers
        # The SDK's transport hands back its own response, range helper and all.
        assert isinstance(out, RawResponse)
        assert (out.status, out.content, out.content_range) == (200, b"hello", None)

    async def test_reads_a_file_verbatim(self) -> None:
        recorder = blob(200, b"\x00\x01\xff")
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            out = await raw.fs.read_raw_file(body=models.ReadFileRequest(path="/app/blob"))
        request = recorder.calls[0]
        assert (request.method, request.url.path) == (
            "POST",
            "/v1/instances/u1/plugins/sandbox/fs/read_raw",
        )
        assert json.loads(request.content) == {"path": "/app/blob"}
        assert out.content == b"\x00\x01\xff"

    async def test_a_finished_wait_returns_the_empty_envelope(self) -> None:
        recorder = queued([(200, {"status": "success", "data": None, "op_time_us": 1})])
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            res = await raw.commands.wait_for_command("c1")
        assert recorder.urls == [ROUTE + "/commands/c1/wait"]
        assert (res.status, res.data) == ("success", None)

    async def test_an_empty_404_is_not_found(self) -> None:
        recorder = Recorder(lambda request: httpx.Response(404))
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            with pytest.raises(NotFoundError):
                await raw.commands.get_command_by_uuid("nope")

    async def test_a_wait_that_times_out_keeps_its_status(self) -> None:
        still_running = {"status": "error", "message": "still running", "errors": [{"status": 408}]}
        recorder = queued([(408, still_running)])
        async with cloud(recorder, metro="fra") as ukc:
            raw = ukc.api.plugins.sandbox.for_instance("u1")
            with pytest.raises(UnikraftCloudError) as caught:
                await raw.commands.wait_for_command_with_timeout(
                    "c1", body=models.CommandWaitTimeoutRequest(timeout_s=1.5)
                )
        assert caught.value.status == 408
        assert json.loads(recorder.calls[0].content) == {"timeout_s": 1.5}


class TestStandaloneClient:
    def _config(self, recorder: Recorder) -> ApiClientConfig:
        return ApiClientConfig(
            base_url="https://api.fra.unikraft.cloud", token="tok", transport=recorder.transport
        )

    async def test_a_plugins_group_owns_the_pool_its_members_share(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))])
        async with PluginsApi(self._config(recorder)) as plugins:
            scoped = plugins.sandbox.for_instance("u1")
            assert scoped.client.http is plugins.http
            await scoped.commands.list_commands()
        assert plugins.http.is_closed
        assert recorder.urls == [ROUTE + "/commands"]

    async def test_a_scoped_client_from_a_v1_base_url_takes_the_metro_route(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))])
        config = ApiClientConfig(
            base_url="https://api.fra.unikraft.cloud/v1", token="tok", transport=recorder.transport
        )
        async with SandboxApi(config) as root:
            await root.for_instance("u1").commands.list_commands()
        assert recorder.urls == [ROUTE + "/commands"]

    async def test_a_client_made_at_a_route_scopes_from_the_metro_too(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))] * 2)
        # Built at the route itself, as a client made through a plugin's route is.
        config = ApiClientConfig(base_url=ROUTE, token="tok", transport=recorder.transport)
        async with SandboxApi(config) as raw:
            await raw.commands.list_commands()
            await raw.for_instance("u2").commands.list_commands()
        assert recorder.urls == [ROUTE + "/commands", ROUTE.replace("/u1/", "/u2/") + "/commands"]

    async def test_scoped_clients_share_the_pool_their_root_closes(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))] * 2)
        async with SandboxApi(self._config(recorder)) as root:
            scoped = root.for_instance("u1")
            assert scoped.client.http is root.client.http
            await scoped.commands.list_commands()
            # Scoping a scoped client starts from the metro again, not from its route.
            again = scoped.for_instance("u2")
            assert again.client.http is root.client.http
            await again.commands.list_commands()
        assert root.client.http.is_closed
        assert recorder.urls == [
            ROUTE + "/commands",
            "https://api.fra.unikraft.cloud/v1/instances/u2/plugins/sandbox/commands",
        ]

    async def test_a_scoped_client_can_be_closed_without_harm(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))])
        root = SandboxApi(self._config(recorder))
        scoped = root.for_instance("u1")
        # Only the client that made the pool releases it.
        await scoped.aclose()
        assert not root.client.http.is_closed
        await root.commands.list_commands(base_url=ROUTE)
        await root.aclose()
        assert root.client.http.is_closed

    async def test_a_client_scoped_to_another_metro_scopes_from_there(self) -> None:
        recorder = queued([(200, envelope({"commands": []}))])
        dal = "https://api.dal.unikraft.cloud"
        async with SandboxApi(self._config(recorder)) as root:
            there = root.for_instance("u1", base_url=dal)
            await there.for_instance("u2").commands.list_commands()
        assert recorder.urls == [f"{dal}/v1/instances/u2/plugins/sandbox/commands"]
