# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Addressing a plugin from an instance handle: what resolving its route costs
# in requests, and that the route is what a client gets pointed at.

from __future__ import annotations

import asyncio
import gc
import warnings
from typing import Any

import pytest

from unikraft_cloud import NotFoundError, UnikraftCloud
from unikraft_cloud.api.plugins.sandbox import SandboxApi
from unikraft_cloud.core.http import ApiClientConfig

from .fake_sandbox import FakeSandbox

ROUTE = "https://api.fra.unikraft.cloud/v1/instances/u1/plugins/sandbox"


def cloud(fake: FakeSandbox, **config: Any) -> UnikraftCloud:
    return UnikraftCloud(token="tok", transport=fake.transport, **config)


class TestResolvingTheRoute:
    async def test_a_uuid_pinned_to_a_metro_sends_nothing(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            route = await ukc.instances.get(uuid="u1").plugin("sandbox").route()
        assert route.url == ROUTE
        assert (route.metro, route.instance_uuid, route.name) == ("fra", "u1", "sandbox")
        assert fake.recorder.calls == []

    async def test_a_name_pinned_to_a_metro_costs_one_read(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            route = await ukc.instances.get(name="web").plugin("sandbox").route()
        assert route.instance_uuid == "u1"
        assert fake.recorder.paths == ["/v1/instances"]
        assert fake.recorder.calls[0].url.params["name"] == "web"

    async def test_a_name_found_by_searching_metros_is_not_read_again(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            plugin = ukc.instances.get(name="web").plugin("sandbox")
            route = await plugin.route()
            found = await plugin.instance()
        assert (route.metro, route.instance_uuid) == ("fra", "u1")
        assert found.uuid == "u1"
        # Discovery, then one search per metro; the match travelled back with it.
        assert fake.recorder.paths == ["/v1/metros", "/v1/instances", "/v1/instances"]

    async def test_a_created_instance_knows_its_uuid(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            route = await ukc.instances.create(image="nginx:latest").plugin("sandbox").route()
        assert route.instance_uuid == "u1"
        assert [(c.method, c.url.path) for c in fake.recorder.calls] == [("POST", "/v1/instances")]

    async def test_a_chained_wait_runs_first_and_its_answer_carries_the_uuid(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            handle = ukc.instances.get(name="web").wait(state="running")
            route = await handle.plugin("sandbox").route()
        assert route.instance_uuid == "u1"
        assert fake.recorder.paths == ["/v1/instances/wait"]

    async def test_concurrent_callers_share_one_resolution(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            plugin = ukc.instances.get(name="web").plugin("sandbox")
            await asyncio.gather(plugin.route(), plugin.route(), plugin.instance())
        assert fake.recorder.paths == ["/v1/instances"]

    async def test_the_instance_is_read_once_when_only_its_uuid_was_known(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            plugin = ukc.instances.get(uuid="u1").plugin("sandbox")
            await plugin.route()
            first = await plugin.instance()
            second = await plugin.instance()
        assert first is second
        assert fake.recorder.paths == ["/v1/instances"]

    async def test_concurrent_reads_of_a_uuid_pinned_instance_share_one_request(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            plugin = ukc.instances.get(uuid="u1").plugin("sandbox")
            first, second = await asyncio.gather(plugin.instance(), plugin.instance())
        assert first is second
        assert fake.recorder.paths == ["/v1/instances"]

    async def test_a_read_that_failed_is_made_again(self) -> None:
        fake = FakeSandbox(instance_metro="dal")
        async with cloud(fake, metro="fra") as ukc:
            plugin = ukc.instances.get(uuid="u1").plugin("sandbox")
            with pytest.raises(NotFoundError):
                await plugin.instance()
            fake.instance_metro = "fra"
            assert (await plugin.instance()).uuid == "u1"
        assert fake.recorder.paths == ["/v1/instances", "/v1/instances"]

    async def test_the_plugin_name_is_the_last_segment(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            route = await ukc.instances.get(uuid="u1").plugin("logger").route()
        assert route.url.endswith("/v1/instances/u1/plugins/logger")


class TestClients:
    async def test_a_factory_is_given_the_transport_config_at_the_route(self) -> None:
        fake = FakeSandbox()
        seen: list[ApiClientConfig] = []

        def factory(config: ApiClientConfig) -> ApiClientConfig:
            seen.append(config)
            return config

        async with cloud(fake, metro="fra") as ukc:
            got = await ukc.instances.get(uuid="u1").plugin("sandbox").client(factory)
        assert got is seen[0]
        assert (seen[0].base_url, seen[0].token) == (ROUTE, "tok")

    async def test_a_generated_client_speaks_to_the_plugin(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            raw = await ukc.instances.get(uuid="u1").plugin("sandbox").client(SandboxApi)
            res = await raw.commands.list_commands()
        assert fake.recorder.urls == [ROUTE + "/commands"]
        assert fake.recorder.calls[0].headers["authorization"] == "Bearer tok"
        assert res.data is not None and res.data.commands == []

    async def test_the_sandbox_shortcut_is_the_sandbox_plugin(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake) as ukc:
            sb = ukc.metro("fra").instances.get(uuid="u1").sandbox()
            assert await sb.ready() is True
        assert fake.recorder.urls == [ROUTE + "/commands"]

    async def test_another_plugin_name_can_be_named_for_the_sandbox(self) -> None:
        fake = FakeSandbox(plugin="sb2")
        async with cloud(fake, metro="fra") as ukc:
            sb = ukc.instances.get(uuid="u1").sandbox(plugin="sb2")
            assert await sb.ready() is True
        assert fake.recorder.paths == ["/v1/instances/u1/plugins/sb2/commands"]

    async def test_a_handle_that_addressed_a_plugin_does_not_warn_when_dropped(self) -> None:
        fake = FakeSandbox()
        async with cloud(fake, metro="fra") as ukc:
            # Recorded, not raised: __del__ swallows an exception, so an "error"
            # filter would hide the very warning this looks for.
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                handle = ukc.instances.get(uuid="u1")
                handle.plugin("sandbox")
                del handle
                gc.collect()
            assert not [w for w in caught if w.category is RuntimeWarning]
