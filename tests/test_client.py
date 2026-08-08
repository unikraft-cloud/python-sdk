# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The client as a user meets it: scopes, discovery, locating a name across
# metros, and the two layers.

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest

from unikraft_cloud import (
    REMOVE,
    AmbiguousRefError,
    MetroFanoutError,
    NotFoundError,
    Ref,
    ServerError,
    UnikraftCloud,
    UnikraftCloudError,
)

from .conftest import (
    Recorder,
    changed_instance,
    envelope,
    instance,
    instance_logs,
    metro,
    metro_of,
    queued,
    quotas,
    routed,
)

METROS = [metro("fra"), metro("dal")]


def client(recorder: Recorder, **config: Any) -> UnikraftCloud:
    return UnikraftCloud(token="tok", transport=recorder.transport, **config)


def cloud(
    *,
    metros: Sequence[dict[str, Any]] = tuple(METROS),
    instances: Callable[[str], list[dict[str, Any]]] | None = None,
    failing: Sequence[str] = (),
) -> Recorder:
    """A transport standing in for the whole platform, per metro."""

    def route(request: httpx.Request) -> tuple[int, Any]:
        if request.url.path == "/v1/metros":
            return 200, envelope({"metros": list(metros)})
        where = metro_of(request)
        if where in failing:
            return 503, {"status": "error", "message": f"{where} is down"}
        if request.url.path in ("/v1/instances/suspend", "/v1/instances/start"):
            return 200, envelope({"instances": [changed_instance()]})
        if request.url.path == "/v1/instances" and request.method == "PATCH":
            return 200, envelope(
                {"instances": [{"uuid": "u1", "name": "web", "status": "success"}]}
            )
        if request.url.path == "/v1/users/quotas":
            return 200, envelope({"quotas": [quotas()]})
        found = instance(f"{where}-1", "web") if instances is None else None
        rows = instances(where) if instances is not None else ([found] if found else [])
        # A second page is always empty, so auto-pagination terminates.
        if request.url.params.get("from"):
            rows = []
        return 200, envelope({"instances": rows})

    return routed(route)


class TestPinnedToOneMetro:
    async def test_targets_the_configured_metro(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web")
        assert recorder.calls[0].url.host == "api.fra.unikraft.cloud"
        assert recorder.calls[0].headers["authorization"] == "Bearer tok"

    async def test_targets_a_full_url_given_as_the_metro(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="https://api.staging.example.com/v1") as ukc:
            await ukc.instances.get(name="web")
        assert recorder.urls[0].startswith("https://api.staging.example.com/v1/instances")

    async def test_never_discovers_metros_when_an_endpoint_is_named(self) -> None:
        recorder = cloud()
        async with client(recorder, base_url="https://api.staging.example.com") as ukc:
            await ukc.instances.get(name="web")
            [inst async for inst in ukc.instances.list()]
        assert "/v1/metros" not in recorder.paths

    async def test_queries_by_uuid_alone_when_given_a_uuid(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(uuid="u1")
        params = recorder.calls[0].url.params
        assert params.get("uuid") == "u1"
        assert "name" not in params

    async def test_rejects_a_reference_with_no_identifier(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(TypeError, match="needs either"):
                ukc.instances.get()

    async def test_raises_on_a_non_2xx_response(self) -> None:
        recorder = queued([(500, {"status": "error", "message": "boom"})])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(ServerError, match="boom"):
                await ukc.instances.get(name="web")

    async def test_auto_paginates_a_listing(self) -> None:
        pages = [
            (200, envelope({"instances": [instance("u1", "a"), instance("u2", "b")]})),
            (200, envelope({"instances": [instance("u3", "c")]})),
        ]
        recorder = queued(pages)
        async with client(recorder, metro="fra") as ukc:
            names = [inst.name async for inst in ukc.instances.list(page_size=2)]
        assert names == ["a", "b", "c"]
        # The cursor is the last uuid of the previous page.
        assert recorder.calls[1].url.params.get("from") == "u2"

    async def test_a_listing_carries_the_metro(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            assert [inst.metro async for inst in ukc.instances.list()] == ["fra"]

    async def test_reads_a_log_through_query_parameters(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance_logs()]}))])
        async with client(recorder, metro="fra") as ukc:
            result = await ukc.instances.get(name="web").logs(offset=-4096, limit=100)
        assert result.output == "aGk="
        params = recorder.calls[0].url.params
        assert (params.get("offset"), params.get("limit")) == ("-4096", "100")
        assert not recorder.calls[0].content

    async def test_waits_through_query_parameters(self) -> None:
        waited = {"uuid": "u1", "name": "web", "state": "running"}
        recorder = queued([(200, envelope({"instances": [waited]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web").wait(state="running", timeout_seconds=30)
        params = recorder.calls[0].url.params
        assert (params.get("state"), params.get("timeout_s")) == ("running", "30")

    async def test_sends_a_bulk_body_of_references(self) -> None:
        recorder = queued([(200, envelope({"instances": [changed_instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.start([Ref(uuid="a"), {"name": "b"}])
        assert json.loads(recorder.calls[0].content) == [{"uuid": "a"}, {"name": "b"}]


class TestUpdates:
    async def test_infers_the_operation_and_carries_the_reference(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web").update(memory_mb=512, autokill=REMOVE)
        assert json.loads(recorder.to("/v1/instances")[-1].content) == [
            {"name": "web", "prop": "memory_mb", "op": "set", "value": 512},
            {"name": "web", "prop": "autokill", "op": "del"},
        ]

    async def test_a_staged_edit_sends_one_request_in_order(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            await (
                ukc.instances.get(name="web")
                .edit()
                .set(memory_mb=512)
                .add(env={"LOG_LEVEL": "debug"})
                .delete(tags=["old"])
                .apply()
            )
        patches = [call for call in recorder.calls if call.method == "PATCH"]
        assert len(patches) == 1
        assert [item["op"] for item in json.loads(patches[0].content)] == ["set", "add", "del"]


class TestTheTwoLayers:
    async def test_exposes_the_raw_platform_api(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            res = await ukc.api.platform.instances.get_instances(count=10)
        assert res.status == "success"
        assert res.data is not None
        assert res.data.instances is not None
        assert res.data.instances[0].name == "web"

    async def test_keeps_a_per_resource_escape_hatch(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            res = await ukc.instances.api.get_instances(count=1)
        assert res.data is not None

    async def test_routes_control_plane_calls_globally(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            await ukc.api.controlplane.metros.list_metros()
        assert recorder.urls[-1] == "https://controlplane.unikraft.cloud/v1/metros"

    async def test_pins_the_raw_platform_api_to_a_scoped_metro(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            await ukc.metro("dal").api.platform.instances.get_instances()
        assert recorder.calls[-1].url.host == "api.dal.unikraft.cloud"

    async def test_caches_the_client_returned_for_a_metro(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            assert ukc.metro("fra") is ukc.metro("fra")


class TestMetroScope:
    async def test_discovers_metros_and_merges_a_listing(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            found = [inst async for inst in ukc.instances.list()]
        assert sorted(inst.metro for inst in found) == ["dal", "fra"]

    async def test_normalises_the_reported_code_and_endpoint(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            endpoints = await ukc.available_metros()
        # The control plane reports "FRA" and a `/v1` endpoint.
        assert [(e.metro, e.base_url) for e in endpoints] == [
            ("fra", "https://api.fra.unikraft.cloud"),
            ("dal", "https://api.dal.unikraft.cloud"),
        ]

    async def test_discovers_only_once_per_client(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            [inst async for inst in ukc.instances.list()]
            [inst async for inst in ukc.instances.list()]
            await ukc.available_metros()
        assert recorder.paths.count("/v1/metros") == 1

    async def test_skips_discovery_when_the_metros_are_named_per_call(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            found = [inst async for inst in ukc.instances.list(metros=["fra", "dal"])]
        assert "/v1/metros" not in recorder.paths
        assert sorted(inst.metro for inst in found) == ["dal", "fra"]

    async def test_yields_the_healthy_metros_then_raises(self) -> None:
        recorder = cloud(failing=["dal"])
        found = []
        async with client(recorder) as ukc:
            with pytest.raises(MetroFanoutError) as caught:
                async for inst in ukc.instances.list():
                    found.append(inst)
        assert [inst.metro for inst in found] == ["fra"]
        assert caught.value.status == 503

    async def test_creates_in_the_default_metro_when_the_scope_spans_all(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            await ukc.instances.create(image="nginx:latest")
        posts = [call for call in recorder.calls if call.method == "POST"]
        assert metro_of(posts[0]) == "fra"

    async def test_honours_a_per_call_metro_override_on_create(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            await ukc.instances.create(image="nginx:latest", metros="dal")
        posts = [call for call in recorder.calls if call.method == "POST"]
        assert metro_of(posts[0]) == "dal"

    async def test_a_single_metro_operation_refuses_an_ambiguous_scope(self) -> None:
        recorder = cloud()
        async with client(recorder, metros=["fra", "dal"]) as ukc:
            with pytest.raises(UnikraftCloudError, match="targets a single metro") as caught:
                await ukc.instances.create(image="nginx:latest")
        assert caught.value.kind == "fanout"

    async def test_merges_quotas_from_every_metro(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            found = await ukc.users.quotas()
        assert sorted(quota.metro for quota in found) == ["dal", "fra"]

    async def test_explains_itself_when_discovery_fails(self) -> None:
        recorder = routed(lambda request: (500, {"status": "error", "message": "down"}))
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError, match="Name the metros you want") as caught:
                [inst async for inst in ukc.instances.list()]
        assert caught.value.kind == "fanout"


class TestLocatingAName:
    async def test_acts_only_on_the_metro_that_holds_it(self) -> None:
        recorder = cloud(instances=lambda where: [instance()] if where == "fra" else [])
        async with client(recorder) as ukc:
            await ukc.instances.get(name="web").suspend()
        assert recorder.metros("/v1/instances/suspend") == ["fra"]

    async def test_reports_a_name_missing_everywhere_as_a_404(self) -> None:
        recorder = cloud(instances=lambda where: [])
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError, match="not found in fra, dal"):
                await ukc.instances.get(name="ghost")

    async def test_says_which_metros_could_not_be_reached(self) -> None:
        recorder = cloud(instances=lambda where: [], failing=["dal"])
        async with client(recorder) as ukc:
            with pytest.raises(MetroFanoutError, match="could not be reached: dal"):
                await ukc.instances.get(name="ghost")

    async def test_a_metro_qualified_reference_needs_no_lookup(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            await ukc.instances.get(name="web", metro="dal").suspend()
        assert "/v1/metros" not in recorder.paths
        assert recorder.metros("/v1/instances/suspend") == ["dal"]
        assert recorder.to("/v1/instances") == []

    async def test_groups_a_bulk_operation_by_the_metro_each_reference_lives_in(self) -> None:
        def where_they_live(where: str) -> list[dict[str, Any]]:
            return [instance("u-fra", "a")] if where == "fra" else [instance("u-dal", "b")]

        recorder = cloud(instances=where_they_live)
        async with client(recorder) as ukc:
            await ukc.instances.start([{"name": "a"}, {"name": "b"}])
        starts = recorder.to("/v1/instances/start")
        # Both metros match both names here, so each gets one grouped call.
        assert sorted(metro_of(call) for call in starts) == ["dal", "fra"]


class TestAmbiguity:
    async def test_get_reports_the_ambiguity_and_carries_the_matches(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            with pytest.raises(AmbiguousRefError) as caught:
                await ukc.instances.get(name="web")
        assert "exists in 2 metros (fra, dal)" in str(caught.value)
        assert 'metro="fra"' in str(caught.value)
        assert sorted(match.metro for match in caught.value.matches) == ["dal", "fra"]
        assert sorted(caught.value.metros) == ["dal", "fra"]

    async def test_each_acts_on_every_match(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            results = await ukc.instances.each(name="web").suspend()
        assert sorted(result.metro for result in results) == ["dal", "fra"]
        assert sorted(recorder.metros("/v1/instances/suspend")) == ["dal", "fra"]

    async def test_each_reads_and_counts_its_matches(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            matches = ukc.instances.each(name="web")
            assert await matches.size() == 2
            assert sorted(await matches.where()) == ["dal", "fra"]
            assert sorted(inst.metro for inst in await matches) == ["dal", "fra"]

    async def test_each_applies_a_staged_edit_to_every_match(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            await ukc.instances.each(name="web").edit().set(memory_mb=512).apply()
        patches = [call for call in recorder.calls if call.method == "PATCH"]
        assert sorted(metro_of(call) for call in patches) == ["dal", "fra"]


class TestConfiguration:
    async def test_reads_the_token_and_metro_from_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UKC_TOKEN", "from-env")
        monkeypatch.setenv("UKC_METRO", "sin")
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with UnikraftCloud(transport=recorder.transport) as ukc:
            await ukc.instances.get(name="web")
        assert recorder.calls[0].headers["authorization"] == "Bearer from-env"
        assert recorder.calls[0].url.host == "api.sin.unikraft.cloud"

    async def test_an_argument_beats_the_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UKC_TOKEN", "from-env")
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with UnikraftCloud(
            token="explicit", metro="fra", transport=recorder.transport
        ) as ukc:
            await ukc.instances.get(name="web")
        assert recorder.calls[0].headers["authorization"] == "Bearer explicit"

    async def test_sends_extra_headers_and_a_custom_user_agent(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(
            recorder, metro="fra", headers={"x-trace": "1"}, user_agent="mine/1.0"
        ) as ukc:
            await ukc.instances.get(name="web")
        assert recorder.calls[0].headers["x-trace"] == "1"
        assert recorder.calls[0].headers["user-agent"] == "mine/1.0"

    async def test_overrides_the_control_plane_url(self) -> None:
        recorder = cloud()
        async with client(recorder, control_plane_url="https://cp.example.com") as ukc:
            await ukc.available_metros()
        assert recorder.urls[-1] == "https://cp.example.com/v1/metros"

    async def test_scopes_can_be_narrowed_after_construction(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            found = [inst async for inst in ukc.metros(["fra"]).instances.list()]
        assert [inst.metro for inst in found] == ["fra"]
        assert "/v1/metros" not in recorder.paths

    async def test_closes_the_pool_it_created(self) -> None:
        recorder = cloud()
        ukc = client(recorder)
        await ukc.aclose()

    async def test_leaves_an_injected_client_alone(self) -> None:
        recorder = cloud()
        async with httpx.AsyncClient(transport=recorder.transport) as http:
            ukc = UnikraftCloud(token="tok", metro="fra", http=http)
            await ukc.aclose()
            assert not http.is_closed
