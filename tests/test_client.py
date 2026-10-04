# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
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
    AlreadyExistsError,
    AmbiguousRefError,
    AuthenticationError,
    InstanceStoppedError,
    MetroFanoutError,
    NotFoundError,
    PlatformStopCode,
    Ref,
    ServerError,
    UnikraftCloud,
    UnikraftCloudError,
    WaitTimeoutError,
)
from unikraft_cloud.resources import instances as instances_module

from .conftest import (
    Recorder,
    changed_instance,
    envelope,
    instance,
    instance_logs,
    metro,
    metro_of,
    missing,
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
        asked = request.url.params.get_list("name") + request.url.params.get_list("uuid")
        if asked and not rows:
            # A metro that holds none of the names says so per reference, inside
            # an otherwise successful response.
            return 200, envelope(
                {"instances": [missing(name=name) for name in asked]},
                status="error",
                message="Failed to perform all operations",
            )
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

    async def test_reads_a_log_through_the_request_body(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance_logs()]}))])
        async with client(recorder, metro="fra") as ukc:
            result = await ukc.instances.get(name="web").logs(offset=-4096, limit=100)
        assert result.output == "aGk="
        # The API reads only an identifier from the query on this operation.
        assert json.loads(recorder.calls[0].content) == [
            {"name": "web", "offset": -4096, "limit": 100}
        ]
        assert not recorder.calls[0].url.params.get("offset")

    async def test_reads_a_log_range_of_zero(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance_logs(output="")]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web").logs(offset=0, limit=0)
        # Zero is a range the API accepts, so it travels like any other.
        assert json.loads(recorder.calls[0].content) == [{"name": "web", "offset": 0, "limit": 0}]

    async def test_waits_through_the_request_body(self) -> None:
        waited = {"uuid": "u1", "name": "web", "state": "running"}
        recorder = queued([(200, envelope({"instances": [waited]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web").wait(state="running", timeout_seconds=30)
        assert json.loads(recorder.calls[0].content) == [
            {"name": "web", "state": "running", "timeout_s": 30}
        ]
        assert not recorder.calls[0].url.params.get("state")

    async def test_a_wait_that_ran_out_of_time_is_a_timeout(self) -> None:
        lapsed = {"uuid": "u1", "name": "web", "state": "stopped", "status": "error"}
        lapsed_envelope = envelope(
            {"instances": [lapsed]}, status="error", message="Operation timed out"
        )
        recorder = queued([(200, lapsed_envelope)])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(WaitTimeoutError) as caught:
                await ukc.instances.get(name="web").wait(state="running", timeout_seconds=1)
        # It is a builtin TimeoutError too, and it says what the API last saw.
        assert isinstance(caught.value, TimeoutError)
        assert caught.value.state == "stopped"
        assert "'running'" in str(caught.value)
        assert caught.value.errors is not None
        assert (caught.value.errors[0].uuid, caught.value.errors[0].state) == ("u1", "stopped")

    async def test_a_wait_outlives_the_timeout_it_asked_the_api_for(self) -> None:
        waited = {"uuid": "u1", "name": "web", "state": "running"}
        recorder = queued([(200, envelope({"instances": [waited]}))])
        async with client(recorder, metro="fra", timeout=5.0) as ukc:
            await ukc.instances.get(name="web").wait(state="running", timeout_seconds=60)
        # The API holds the connection open for the whole wait.
        assert recorder.calls[0].extensions["timeout"]["read"] > 60

    async def test_a_wait_for_as_long_as_the_platform_allows_has_no_read_timeout(self) -> None:
        waited = {"uuid": "u1", "name": "web", "state": "running"}
        recorder = queued([(200, envelope({"instances": [waited]}))])
        async with client(recorder, metro="fra", timeout=5.0) as ukc:
            await ukc.instances.get(name="web").wait(state="running", timeout_seconds=-1)
        assert json.loads(recorder.calls[0].content)[0]["timeout_s"] == -1
        assert recorder.calls[0].extensions["timeout"]["read"] is None

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
            {"name": "web", "prop": "autokill", "op": "set"},
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

    async def test_an_empty_per_call_scope_is_rejected_rather_than_widened(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError, match="empty metro scope") as listing:
                [inst async for inst in ukc.instances.list(metros=[])]
            with pytest.raises(UnikraftCloudError, match="empty metro scope") as creating:
                await ukc.instances.create(image="nginx:latest", metros=[])
        assert listing.value.kind == creating.value.kind == "fanout"
        # Neither fell back to the client's scope, so nothing was asked of anyone.
        assert recorder.paths == []

    async def test_skips_discovery_when_every_reference_names_its_metro(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/metros":
                return 503, {"status": "error", "message": "discovery is down"}
            return 200, envelope({"instances": [changed_instance()]})

        recorder = routed(route)
        async with client(recorder) as ukc:
            await ukc.instances.start([Ref(uuid="a", metro="fra"), Ref(uuid="b", metro="dal")])
        assert "/v1/metros" not in recorder.paths
        assert sorted(recorder.metros("/v1/instances/start")) == ["dal", "fra"]

    async def test_yields_the_healthy_metros_then_raises(self) -> None:
        recorder = cloud(failing=["dal"])
        found = []
        async with client(recorder) as ukc:
            with pytest.raises(MetroFanoutError) as caught:
                async for inst in ukc.instances.list():
                    found.append(inst)
        assert [inst.metro for inst in found] == ["fra"]
        assert caught.value.status == 503

    async def test_refuses_to_pick_a_metro_to_create_in(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError, match="targets a single metro") as caught:
                await ukc.instances.create(image="nginx:latest")
        assert caught.value.kind == "fanout"
        assert [call for call in recorder.calls if call.method == "POST"] == []

    async def test_honours_a_per_call_metro_override_on_create(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            await ukc.instances.create(image="nginx:latest", metros="dal")
        posts = [call for call in recorder.calls if call.method == "POST"]
        assert metro_of(posts[0]) == "dal"

    async def test_a_named_metro_is_the_target_a_wider_scope_does_not_name(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra", metros=["fra", "dal"]) as ukc:
            await ukc.instances.create(image="nginx:latest")
            found = [inst.metro async for inst in ukc.instances.list()]
        posts = [call for call in recorder.calls if call.method == "POST"]
        # `metros` widens what reads cover; `metro` still says where to create.
        assert metro_of(posts[0]) == "fra"
        assert sorted(found) == ["dal", "fra"]

    async def test_a_named_metro_is_the_target_of_an_account_wide_scope_too(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra", metros="all") as ukc:
            await ukc.instances.create(image="nginx:latest")
        posts = [call for call in recorder.calls if call.method == "POST"]
        assert metro_of(posts[0]) == "fra"

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

    async def test_does_not_act_on_a_match_while_a_metro_is_unreachable(self) -> None:
        recorder = cloud(
            instances=lambda where: [instance()] if where == "fra" else [],
            failing=["dal"],
        )
        async with client(recorder) as ukc:
            with pytest.raises(MetroFanoutError, match="found in fra, but") as caught:
                await ukc.instances.get(name="web").suspend()
        # The metro that failed might hold the same name, so the match is handed
        # over for the caller to decide on rather than acted upon.
        assert [match.metro for match in caught.value.results] == ["fra"]
        assert recorder.to("/v1/instances/suspend") == []

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

    async def test_asks_each_metro_about_every_reference_at_once(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/metros":
                return 200, envelope({"metros": list(METROS)})
            if request.url.path == "/v1/instances/start":
                return 200, envelope({"instances": [changed_instance()]})
            # Only Frankfurt holds them, and it answers about the whole batch.
            asked = request.url.params.get_list("name")
            rows = [instance(f"u-{name}", name) for name in asked]
            return 200, envelope({"instances": rows if metro_of(request) == "fra" else []})

        recorder = routed(route)
        async with client(recorder) as ukc:
            await ukc.instances.start([{"name": f"i{n}"} for n in range(5)])
        # One lookup per metro, not one per reference per metro.
        assert len(recorder.to("/v1/instances")) == 2
        assert recorder.metros("/v1/instances/start") == ["fra"]


class TestMissingNames:
    async def test_acts_on_a_name_only_one_metro_holds(self) -> None:
        # The metros that do not hold it answer "no such instance", not a failure.
        recorder = cloud(instances=lambda where: [instance()] if where == "fra" else [])
        async with client(recorder) as ukc:
            suspended = await ukc.instances.get(name="web").suspend()
        assert suspended.metro == "fra"
        assert recorder.metros("/v1/instances/suspend") == ["fra"]

    async def test_a_name_missing_everywhere_is_a_not_found(self) -> None:
        recorder = cloud(instances=lambda where: [])
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError, match="not found in fra, dal"):
                await ukc.instances.get(name="ghost")

    async def test_a_bulk_operation_skips_the_metros_holding_none_of_them(self) -> None:
        def where_they_live(where: str) -> list[dict[str, Any]]:
            return [instance("u-fra", "a")] if where == "fra" else []

        recorder = cloud(instances=where_they_live)
        async with client(recorder) as ukc:
            started = await ukc.instances.start([{"name": "a"}])
        assert [inst.metro for inst in started] == ["fra"]
        assert recorder.metros("/v1/instances/start") == ["fra"]

    async def test_a_set_of_a_missing_name_deletes_nothing_when_told_so(self) -> None:
        recorder = cloud(instances=lambda where: [])
        async with client(recorder) as ukc:
            assert await ukc.instances.each(name="ghost").delete(missing_ok=True) == []
            with pytest.raises(NotFoundError, match="not found in fra, dal"):
                await ukc.instances.each(name="ghost").delete()
        assert not [call for call in recorder.calls if call.method == "DELETE"]

    async def test_a_lookup_on_one_metro_says_which_name_is_missing(self) -> None:
        recorder = cloud(instances=lambda where: [])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(NotFoundError, match="No instance with name 'ghost'") as caught:
                await ukc.instances.get(name="ghost")
        assert caught.value.status == 404


class TestLookupsAreRepeated:
    async def test_a_name_not_listed_yet_is_looked_up_again(self) -> None:
        rows: dict[str, list[dict[str, Any]]] = {"fra": [], "dal": []}
        recorder = cloud(instances=lambda where: rows[where])
        async with client(recorder) as ukc:
            handle = ukc.instances.get(name="web")
            with pytest.raises(NotFoundError):
                await handle
            rows["fra"] = [instance("u1", "web")]
            found = await handle
        assert (found.metro, found.uuid) == ("fra", "u1")
        assert sorted(recorder.metros("/v1/instances")) == ["dal", "dal", "fra", "fra"]

    async def test_a_metro_that_failed_to_answer_is_asked_again(self) -> None:
        down = ["dal"]
        recorder = cloud(instances=lambda where: [instance(f"{where}-1", "web")], failing=down)
        async with client(recorder) as ukc:
            matches = ukc.instances.each(name="web")
            with pytest.raises(MetroFanoutError):
                await matches.size()
            down.clear()
            assert await matches.size() == 2

    async def test_a_create_that_failed_is_not_sent_again(self) -> None:
        recorder = queued([(500, {"status": "error", "message": "boom"})])
        async with client(recorder, metro="fra") as ukc:
            handle = ukc.instances.create(image="org/app:latest")
            with pytest.raises(ServerError):
                await handle
            with pytest.raises(ServerError):
                await handle
        assert len(recorder.calls) == 1

    async def test_an_operation_chained_onto_a_name_not_listed_yet_runs_once_it_is(self) -> None:
        rows: dict[str, list[dict[str, Any]]] = {"fra": [], "dal": []}
        recorder = cloud(instances=lambda where: rows[where])
        async with client(recorder) as ukc:
            suspend = ukc.instances.get(name="web").suspend()
            with pytest.raises(NotFoundError):
                await suspend
            assert "/v1/instances/suspend" not in recorder.paths
            rows["fra"] = [instance("u1", "web")]
            suspended = await suspend
            # The operation itself ran once, and its outcome stands.
            assert await suspend is suspended
        assert recorder.paths.count("/v1/instances/suspend") == 1
        assert sorted(recorder.metros("/v1/instances")) == ["dal", "dal", "fra", "fra"]

    async def test_an_operation_that_failed_is_not_sent_again(self) -> None:
        broken = [True]

        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/instances/suspend":
                if broken[0]:
                    return 500, {"status": "error", "message": "boom"}
                return 200, envelope({"instances": [changed_instance()]})
            return 200, envelope({"instances": [instance("u1", "web")]})

        recorder = routed(route)
        async with client(recorder, metro="fra") as ukc:
            suspend = ukc.instances.get(name="web").suspend()
            with pytest.raises(ServerError):
                await suspend
            broken[0] = False
            with pytest.raises(ServerError):
                await suspend
        assert recorder.paths.count("/v1/instances/suspend") == 1


class TestPinnedScope:
    async def test_refuses_a_metro_the_pinned_endpoint_does_not_serve(self) -> None:
        recorder = cloud()
        async with client(recorder, base_url="https://api.staging.example.com") as ukc:
            with pytest.raises(UnikraftCloudError, match="pinned to"):
                await ukc.instances.get(name="web", metro="dal")

    async def test_refuses_a_per_call_scope_it_cannot_reach(self) -> None:
        recorder = cloud()
        async with client(recorder, base_url="https://api.staging.example.com") as ukc:
            with pytest.raises(UnikraftCloudError, match="pinned to"):
                [inst async for inst in ukc.instances.list(metros=["dal"])]


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

    async def test_each_in_one_metro_reports_the_match_it_found(self) -> None:
        recorder = cloud(instances=lambda where: [instance()] if where == "fra" else [])
        async with client(recorder) as ukc:
            matches = ukc.metro("fra").instances.each(name="web")
            assert await matches.size() == 1
            assert await matches.where() == ["fra"]
        assert recorder.metros("/v1/instances") == ["fra"]

    async def test_each_in_one_metro_reports_no_match_it_did_not_find(self) -> None:
        recorder = cloud(instances=lambda where: [])
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError, match="not found in fra"):
                await ukc.metro("fra").instances.each(name="ghost").size()

    async def test_each_applies_a_staged_edit_to_every_match(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            await ukc.instances.each(name="web").edit().set(memory_mb=512).apply()
        patches = [call for call in recorder.calls if call.method == "PATCH"]
        assert sorted(metro_of(call) for call in patches) == ["dal", "fra"]


class TestConveniences:
    async def test_a_bare_name_is_a_reference(self) -> None:
        recorder = queued([(200, envelope({"instances": [changed_instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.stop("web")
        assert json.loads(recorder.calls[0].content) == [{"name": "web"}]

    async def test_a_listing_can_be_awaited_for_a_list(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            found = await ukc.instances.list()
        assert [inst.name for inst in found] == ["web"]

    async def test_a_chained_operation_inherits_the_handles_headers(self) -> None:
        recorder = queued([(200, envelope({"instances": [changed_instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web", headers={"x-trace": "1"}).suspend()
        assert recorder.calls[0].headers["x-trace"] == "1"

    async def test_a_tag_filter_travels_as_one_parameter(self) -> None:
        recorder = queued([(200, envelope({"instances": []}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.list(tags=["team:a", "env:prod"])
        # The API splits on a literal comma, so the separator is not escaped.
        assert "tags=team%3Aa,env%3Aprod" in str(recorder.calls[0].url)

    async def test_a_tag_filter_survives_pagination(self) -> None:
        pages = [
            (200, envelope({"instances": [instance("u1", "a"), instance("u2", "b")]})),
            (200, envelope({"instances": [instance("u2", "b"), instance("u3", "c")]})),
        ]
        recorder = queued(pages)
        async with client(recorder, metro="fra") as ukc:
            names = [inst.name async for inst in ukc.instances.list(tags=["prod"], page_size=2)]
        # Each match once, and every page filtered by the same tags.
        assert names == ["a", "b", "c"]
        assert [call.url.params.get("tags") for call in recorder.calls] == ["prod", "prod"]

    async def test_creating_reads_the_resource_back(self) -> None:
        created = {"uuid": "u1", "name": "web", "state": "stopped"}
        recorder = queued(
            [
                (200, envelope({"instances": [created]})),
                (200, envelope({"instances": [instance()]})),
            ]
        )
        async with client(recorder, metro="fra") as ukc:
            made = await ukc.instances.create(name="web", image="nginx:latest")
        # The create response carries less than a read does.
        assert made.image == "nginx:latest"
        assert [call.method for call in recorder.calls] == ["POST", "GET"]

    async def test_creating_rejects_a_property_it_does_not_have(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(TypeError, match="memroy_mb"):
                ukc.instances.create(name="web", image="nginx:latest", memroy_mb=256)
        # The API keeps unknown fields, so nothing would have reported the typo.
        assert recorder.calls == []

    async def test_creating_and_chaining_costs_no_extra_read(self) -> None:
        created = {"uuid": "u1", "name": "web", "state": "stopped"}
        started = {"uuid": "u1", "name": "web", "state": "starting"}
        recorder = queued(
            [(200, envelope({"instances": [created]})), (200, envelope({"instances": [started]}))]
        )
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.create(name="web", image="nginx:latest").start()
        assert [call.url.path for call in recorder.calls] == [
            "/v1/instances",
            "/v1/instances/start",
        ]

    async def test_refuses_to_create_replicas_it_could_not_hand_back(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(TypeError, match="replicas"):
                ukc.instances.create(image="nginx:latest", replicas=2)
        assert recorder.calls == []


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

    async def test_an_explicit_endpoint_beats_the_environments_metro(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UKC_METRO", "https://api.env.example.com")
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, base_url="https://api.staging.example.com") as ukc:
            found = await ukc.instances.get(name="web")
        # The environment names another place, which the endpoint settles.
        assert recorder.calls[0].url.host == "api.staging.example.com"
        assert found.metro == "https://api.staging.example.com"

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


class TestTimeouts:
    async def test_applies_the_configured_timeout_to_every_request(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra", timeout=5.0) as ukc:
            await ukc.instances.get(name="web")
        assert recorder.calls[0].extensions["timeout"]["read"] == 5.0

    async def test_the_plumbing_layer_carries_it_too(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra", timeout=5.0) as ukc:
            await ukc.api.platform.instances.get_instances(name=["web"])
        assert recorder.calls[0].extensions["timeout"]["read"] == 5.0

    async def test_an_injected_client_keeps_its_own(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with (
            httpx.AsyncClient(transport=recorder.transport, timeout=3.0) as http,
            UnikraftCloud(token="tok", metro="fra", http=http) as ukc,
        ):
            await ukc.instances.get(name="web")
        assert recorder.calls[0].extensions["timeout"]["read"] == 3.0

    async def test_an_explicit_timeout_beats_an_injected_clients(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with (
            httpx.AsyncClient(transport=recorder.transport, timeout=3.0) as http,
            UnikraftCloud(token="tok", metro="fra", http=http, timeout=9.0) as ukc,
        ):
            await ukc.instances.get(name="web")
        assert recorder.calls[0].extensions["timeout"]["read"] == 9.0

    async def test_a_create_that_waits_outlives_the_timeout_it_asked_the_api_for(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))] * 2)
        async with client(recorder, metro="fra", timeout=5.0) as ukc:
            await ukc.instances.create(image="org/app:latest", autostart=True, timeout_s=30)
            await ukc.instances.create(image="org/app:latest")
        waited, plain = [call for call in recorder.calls if call.method == "POST"]
        # The wait the API was asked for, plus the margin every wait is given.
        assert waited.extensions["timeout"]["read"] == 40
        assert plain.extensions["timeout"]["read"] == 5.0

    async def test_the_deprecated_wait_in_milliseconds_is_outlived_too(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))] * 2)
        async with client(recorder, metro="fra", timeout=5.0) as ukc:
            await ukc.instances.create(image="org/app:latest", autostart=True, wait_timeout_ms=2500)
        (waited,) = [call for call in recorder.calls if call.method == "POST"]
        # 2.5 seconds rounds up to 3, plus the margin every wait is given.
        assert waited.extensions["timeout"]["read"] == 13

    async def test_defaults_to_bounding_connecting_but_not_reading(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web")
        sent = recorder.calls[0].extensions["timeout"]
        assert sent["connect"] == 10.0
        assert sent["read"] is None


class TestSummaryPayloads:
    async def test_a_listing_without_details_is_references_only(self) -> None:
        rows = [{"uuid": "u1", "name": "web"}, {"uuid": "u2", "name": "api"}]
        recorder = queued(
            [(200, envelope({"instances": rows})), (200, envelope({"instances": []}))]
        )
        async with client(recorder, metro="fra") as ukc:
            found = [inst async for inst in ukc.instances.list()]
        assert [inst.name for inst in found] == ["web", "api"]
        assert found[0].state is None

    async def test_a_partly_failed_bulk_reports_the_item_that_failed(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.method == "DELETE":
                # One deleted, one that does not exist, in a 200 response.
                return 200, envelope(
                    {"instances": [changed_instance("u1", "web"), missing(name="gone")]},
                    status="partial_success",
                    message="Failed to perform all operations",
                )
            return 200, envelope({"instances": [instance()]})

        recorder = routed(route)
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(NotFoundError, match="No instance with name 'gone'") as caught:
                await ukc.instances.delete([{"name": "web"}, {"name": "gone"}])
        # What did succeed is handed over rather than lost.
        assert [deleted.name for deleted in caught.value.results] == ["web"]
        assert caught.value.results[0].metro == "fra"

    async def test_reads_a_timestamp_as_a_datetime(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            found = await ukc.instances.get(name="web")
        assert found.created_at is not None
        assert found.created_at.year == 2026


class TestPerCallEndpoints:
    async def test_a_chained_operation_honours_its_own_base_url(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(name="web").suspend(base_url="https://api.staging.example.com")
        assert recorder.urls[-1].startswith("https://api.staging.example.com/")

    async def test_a_chained_operation_reports_the_metro_it_reached(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            out = await ukc.instances.get(name="web").suspend(
                base_url="https://api.staging.example.com"
            )
        # The result says where it came from, not where the handle was located.
        assert out.metro == "https://api.staging.example.com"

    async def test_a_chain_after_an_override_stays_at_that_endpoint(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            out = await (
                ukc.instances.get(name="web")
                .suspend(base_url="https://api.staging.example.com")
                .start()
            )
        assert all(url.startswith("https://api.staging.example.com/") for url in recorder.urls[-2:])
        assert out.metro == "https://api.staging.example.com"

    async def test_an_operation_with_no_override_keeps_its_located_metro(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            out = await ukc.instances.get(name="web").suspend()
        assert out.metro == "fra"
        assert recorder.urls[-1].startswith("https://api.fra.unikraft.cloud/")

    async def test_a_bulk_operation_honours_a_base_url_over_its_qualifiers(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            started = await ukc.instances.start(
                [{"name": "a", "metro": "fra"}, {"name": "b", "metro": "dal"}],
                base_url="https://api.staging.example.com",
            )
        sent = recorder.to("/v1/instances/start")
        # One request to the named endpoint, not one per metro the refs carried.
        assert len(sent) == 1
        assert str(sent[0].url).startswith("https://api.staging.example.com/")
        assert json.loads(sent[0].content) == [{"name": "a"}, {"name": "b"}]
        assert [inst.metro for inst in started] == ["https://api.staging.example.com"]

    async def test_a_bulk_operation_with_no_references_sends_nothing(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="fra") as ukc:
            assert await ukc.instances.delete([]) == []
        assert recorder.calls == []

    async def test_a_bulk_operation_with_no_references_sends_nothing_account_wide(self) -> None:
        recorder = cloud()
        async with client(recorder) as ukc:
            assert await ukc.instances.stop([]) == []
        assert recorder.calls == []


class TestPinnedEndpoints:
    async def test_refuses_to_hand_out_a_metro_it_is_not_pinned_to(self) -> None:
        recorder = cloud()
        async with client(recorder, metro="https://api.staging.example.com") as ukc:
            with pytest.raises(UnikraftCloudError, match="pinned to"):
                ukc.metro("dal")

    async def test_accepts_the_metro_it_is_pinned_to(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra", base_url="https://api.staging.example.com") as ukc:
            await ukc.metro("fra").instances.get(name="web")
        assert recorder.urls[0].startswith("https://api.staging.example.com/")

    async def test_a_named_metro_stays_the_identity_of_an_explicit_endpoint(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, metro="fra", base_url="https://api.staging.example.com") as ukc:
            found = await ukc.instances.get(name="web")
        assert found.metro == "fra"

    async def test_an_endpoint_with_no_metro_named_is_identified_by_its_url(self) -> None:
        recorder = queued([(200, envelope({"instances": [instance()]}))])
        async with client(recorder, base_url="https://api.staging.example.com") as ukc:
            found = await ukc.instances.get(name="web")
        assert found.metro == "https://api.staging.example.com"


class TestDiscoveryFailures:
    async def test_a_rejected_token_keeps_its_type(self) -> None:
        recorder = routed(lambda request: (401, {"status": "error", "message": "bad token"}))
        async with client(recorder) as ukc:
            with pytest.raises(AuthenticationError) as caught:
                [inst async for inst in ukc.instances.list()]
        assert caught.value.status == 401

    async def test_any_other_failure_says_how_to_skip_discovery(self) -> None:
        recorder = routed(lambda request: (500, {"status": "error", "message": "down"}))
        async with client(recorder) as ukc:
            with pytest.raises(UnikraftCloudError, match="Name the metros you want") as caught:
                [inst async for inst in ukc.instances.list()]
        assert caught.value.status == 500


class TestCreateFailures:
    def _stopped_create(self, *rows: dict[str, Any]) -> Recorder:
        """A create whose autostart wait ended on a stopped instance, then its read."""
        failed = {"status": "error", "uuid": "u1", "name": "web", "state": "stopped"}
        return queued(
            [
                (200, envelope({"instances": [failed]}, status="error")),
                (200, envelope({"instances": list(rows)})),
            ]
        )

    async def test_an_instance_that_stopped_is_read_for_the_reason(self) -> None:
        recorder = self._stopped_create(instance(state="stopped", stop_reason=4, stop_code=1))
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(InstanceStoppedError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest", autostart=True)
        err = caught.value
        assert err.instance.uuid == "u1"
        assert err.stop is not None
        assert err.stop.platform_code == PlatformStopCode.IMAGE_PULL_FAILED
        assert (
            str(err)
            == 'instance uuid "u1" stopped before it was running: platform stop: image pull failed'
        )
        assert isinstance(err.__cause__, UnikraftCloudError)
        assert err.errors is not None and err.errors[0].uuid == "u1"
        assert [call.method for call in recorder.calls] == ["POST", "GET"]
        assert recorder.calls[1].url.params["uuid"] == "u1"

    async def test_a_stop_the_api_reports_as_a_lapsed_wait_is_still_a_stop(self) -> None:
        failed = {"status": "error", "uuid": "u1", "name": "web", "state": "stopped"}
        lapsed = envelope(
            {"instances": [failed]}, status="error", message="Timed out waiting for instance"
        )
        recorder = queued(
            [(200, lapsed), (200, envelope({"instances": [instance(state="stopped")]}))]
        )
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(InstanceStoppedError):
                await ukc.instances.create(name="web", image="org/app:latest", timeout_s=30)

    async def test_a_create_that_did_not_wait_has_not_timed_out(self) -> None:
        failed = {"status": "error", "uuid": "u1", "name": "web", "state": "starting"}
        lapsed = envelope(
            {"instances": [failed]}, status="error", message="Timed out waiting for instance"
        )
        recorder = queued([(200, lapsed)])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(UnikraftCloudError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest")
        assert not isinstance(caught.value, WaitTimeoutError)

    async def test_an_instance_that_stopped_without_a_reason_still_says_so(self) -> None:
        recorder = self._stopped_create(instance(state="stopped"))
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(
                InstanceStoppedError, match=r"stopped before it was running$"
            ) as caught:
                await ukc.instances.create(name="web", image="org/app:latest")
        assert caught.value.stop is None

    async def test_an_instance_deleted_on_stop_is_still_a_stopped_instance(self) -> None:
        # As the API reports it: the item is in the `deleted` state, nothing left to read.
        gone = {"status": "error", "uuid": "u1", "name": "web", "state": "deleted"}
        recorder = queued([(200, envelope({"instances": [gone]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(InstanceStoppedError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest", timeout_s=30)
        err = caught.value
        assert (err.instance.uuid, err.instance.name, err.instance.state) == (
            "u1",
            "web",
            "deleted",
        )
        assert (err.instance.metro, err.stop) == ("fra", None)
        assert str(err).endswith("stopped before it was running; it is gone already")
        assert len(recorder.calls) == 1

    async def test_an_instance_gone_before_it_is_read_is_still_a_stopped_instance(self) -> None:
        recorder = self._stopped_create()
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(InstanceStoppedError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest")
        err = caught.value
        assert (err.instance.uuid, err.instance.state, err.stop) == ("u1", "stopped", None)
        assert str(err).endswith("; it is gone already")
        assert len(recorder.calls) == 2

    async def test_a_read_back_route_that_is_not_there_keeps_the_original_error(self) -> None:
        failed = {"status": "error", "uuid": "u1", "name": "web", "state": "stopped"}
        recorder = queued(
            [
                (200, envelope({"instances": [failed]}, status="error")),
                (404, {"status": "error", "message": "no such route"}),
            ]
        )
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(UnikraftCloudError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest")
        assert not isinstance(caught.value, InstanceStoppedError)

    async def test_an_instance_not_stopped_after_all_keeps_the_original_error(self) -> None:
        recorder = self._stopped_create(instance(state="running"))
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(UnikraftCloudError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest")
        assert not isinstance(caught.value, InstanceStoppedError)

    async def test_a_failure_with_the_apis_own_code_is_not_read_as_a_stop(self) -> None:
        taken = {"status": "error", "uuid": "u1", "name": "web", "error": 23, "message": "taken"}
        recorder = queued(
            [
                (200, envelope({"instances": [taken]}, status="error")),
                (200, envelope({"instances": [instance(state="stopped")]})),
            ]
        )
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(AlreadyExistsError, match="taken"):
                await ukc.instances.create(name="web", image="org/app:latest")
        assert len(recorder.calls) == 1

    async def test_a_failed_item_in_another_state_is_not_read_as_a_stop(self) -> None:
        starting = {"status": "error", "uuid": "u1", "name": "web", "state": "starting"}
        recorder = queued([(200, envelope({"instances": [starting]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(UnikraftCloudError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest")
        assert not isinstance(caught.value, InstanceStoppedError)
        assert caught.value.errors is not None and caught.value.errors[0].state == "starting"
        assert len(recorder.calls) == 1

    async def test_a_failure_naming_no_instance_is_not_read(self) -> None:
        refused = {"status": "error", "message": "Failed to create. Quota exceeded", "error": 19}
        recorder = queued([(200, envelope({"instances": [refused]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(UnikraftCloudError, match="Quota exceeded"):
                await ukc.instances.create(name="web", image="org/app:latest")
        assert len(recorder.calls) == 1

    async def test_a_create_whose_wait_ran_out_is_a_timeout(self) -> None:
        still = {"status": "error", "uuid": "u1", "name": "web", "state": "starting"}
        recorder = queued(
            [
                (
                    200,
                    envelope({"instances": [still]}, status="error", message="Operation timed out"),
                )
            ]
        )
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(WaitTimeoutError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest", timeout_s=5)
        assert caught.value.state == "starting"
        # The instance it made travels along, to be waited for or deleted.
        assert caught.value.errors is not None and caught.value.errors[0].uuid == "u1"
        assert len(recorder.calls) == 1

    async def test_an_instance_read_back_as_deleted_is_gone_already(self) -> None:
        recorder = self._stopped_create(instance(state="deleted"))
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(InstanceStoppedError) as caught:
                await ukc.instances.create(name="web", image="org/app:latest")
        assert (caught.value.instance.state, caught.value.stop) == ("deleted", None)
        assert str(caught.value).endswith("; it is gone already")


class TestDeleting:
    async def test_missing_ok_forgives_no_operation_that_failed_before_it(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/instances/start":
                return 200, envelope(
                    {"instances": [missing(name="ghost")]},
                    status="error",
                    message="Failed to perform all operations",
                )
            return 200, envelope({"instances": []})

        recorder = routed(route)
        async with client(recorder, metro="fra") as ukc:
            # The start's own not-found is the start's failure, not an absence.
            with pytest.raises(NotFoundError):
                await ukc.instances.get(name="ghost").start().delete(missing_ok=True)
        assert [call.method for call in recorder.calls] == ["PUT"]

    async def test_missing_ok_forgives_no_route_that_is_not_there(self) -> None:
        # A 404 with no item named is the endpoint missing, not the instance.
        recorder = routed(lambda request: (404, {"status": "error", "message": "no such route"}))
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(NotFoundError):
                await ukc.instances.get(name="ghost").delete(missing_ok=True)

    async def test_can_wait_for_the_instance_to_be_gone(self) -> None:
        recorder = queued([(200, envelope({"instances": [changed_instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.get(uuid="u1").delete(timeout_seconds=-1)
        assert json.loads(recorder.calls[0].content) == [{"uuid": "u1", "timeout_s": -1}]

    async def test_a_bulk_delete_can_wait_too(self) -> None:
        recorder = queued([(200, envelope({"instances": [changed_instance()]}))])
        async with client(recorder, metro="fra") as ukc:
            await ukc.instances.delete(["web"], timeout_seconds=30)
        assert json.loads(recorder.calls[0].content) == [{"name": "web", "timeout_s": 30}]

    async def test_a_bounded_wait_lets_the_request_outlast_it(self) -> None:
        recorder = queued([(200, envelope({"instances": [changed_instance()]}))])
        async with client(recorder, metro="fra", timeout=5.0) as ukc:
            await ukc.instances.get(uuid="u1").delete(timeout_seconds=30)
        assert recorder.calls[0].extensions["timeout"]["read"] == 40.0

    async def test_an_instance_already_gone_is_a_failure_by_default(self) -> None:
        recorder = queued([(200, envelope({"instances": [missing(uuid="u1")]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(NotFoundError):
                await ukc.instances.get(uuid="u1").delete()

    async def test_an_instance_already_gone_can_be_no_failure(self) -> None:
        recorder = queued([(200, envelope({"instances": [missing(uuid="u1")]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            assert await ukc.instances.get(uuid="u1").delete(missing_ok=True) is None
        assert len(recorder.calls) == 1

    async def test_a_name_no_metro_holds_can_be_no_failure_either(self) -> None:
        recorder = cloud(instances=lambda where: [])
        async with client(recorder) as ukc:
            assert await ukc.instances.get(name="ghost").delete(missing_ok=True) is None
        # Located across both metros, found nowhere, and nothing was deleted.
        assert sorted(recorder.metros("/v1/instances")) == ["dal", "fra"]
        assert all(call.method == "GET" for call in recorder.calls if call.url.path != "/v1/metros")

    async def test_a_busy_instance_is_retried_with_backoff(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slept: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(instances_module, "_sleep", fake_sleep)
        busy = {"status": "error", "uuid": "u1", "message": "Unknown error -16", "error": 0}
        recorder = queued(
            [
                (200, envelope({"instances": [busy]}, status="error")),
                (200, envelope({"instances": [busy]}, status="error")),
                (200, envelope({"instances": [changed_instance()]})),
            ]
        )
        async with client(recorder, metro="fra") as ukc:
            deleted = await ukc.instances.get(uuid="u1").delete(retry_busy=20)
        assert deleted.uuid == "u1"
        assert len(recorder.calls) == 3
        assert slept == [0.5, 1.0]

    async def test_a_busy_instance_fails_at_once_without_a_retry(self) -> None:
        busy = {"status": "error", "uuid": "u1", "message": "Failed to delete: EBUSY", "error": 10}
        recorder = queued([(200, envelope({"instances": [busy]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(UnikraftCloudError, match="EBUSY"):
                await ukc.instances.get(uuid="u1").delete()
        assert len(recorder.calls) == 1

    async def test_a_busy_instance_is_given_up_on_at_the_deadline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(instances_module, "_sleep", fake_sleep)
        busy = {"status": "error", "uuid": "u1", "message": "Unknown error -16", "error": 0}
        recorder = queued([(200, envelope({"instances": [busy]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(UnikraftCloudError, match="Unknown error -16"):
                await ukc.instances.get(uuid="u1").delete(retry_busy=0.01)
        assert len(recorder.calls) > 1

    async def test_any_other_failure_is_not_retried(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_sleep(seconds: float) -> None:
            raise AssertionError("slept")

        monkeypatch.setattr(instances_module, "_sleep", fake_sleep)
        recorder = queued([(403, {"status": "error", "message": "denied"})])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(AuthenticationError):
                await ukc.instances.get(uuid="u1").delete(retry_busy=20)
        assert len(recorder.calls) == 1

    async def test_missing_ok_forgives_no_create_that_failed(self) -> None:
        # The API names the volume as missing, with its own code, but the create failed.
        failed = missing(name="ghost", noun="volume") | {"name": "web"}
        recorder = queued([(200, envelope({"instances": [failed]}, status="error"))])
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(NotFoundError):
                await ukc.instances.create(
                    image="org/app:latest", volumes=[{"name": "ghost", "at": "/data"}]
                ).delete(missing_ok=True)
        assert [call.method for call in recorder.calls] == ["POST"]

    async def test_a_forgiven_absence_is_still_a_not_found_to_a_resolve(self) -> None:
        recorder = cloud(instances=lambda where: [])
        async with client(recorder) as ukc:
            handle = ukc.instances.get(name="ghost").delete(missing_ok=True)
            assert await handle is None
            with pytest.raises(NotFoundError):
                await handle.where()
            with pytest.raises(NotFoundError):
                await handle.plugin("sandbox").route()

    async def test_missing_ok_forgives_no_bare_404(self) -> None:
        recorder = Recorder(lambda request: httpx.Response(404))
        async with client(recorder, metro="fra") as ukc:
            with pytest.raises(NotFoundError):
                await ukc.instances.get(name="ghost").delete(missing_ok=True)

    async def test_a_set_delete_that_partly_failed_reports_no_forgiven_match(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/metros":
                return 200, envelope({"metros": METROS})
            if request.method == "DELETE":
                if metro_of(request) == "fra":
                    return 200, envelope({"instances": [missing(name="web")]}, status="error")
                return 404, {"status": "error", "message": "no such route"}
            return 200, envelope({"instances": [instance(f"{metro_of(request)}-1", "web")]})

        recorder = routed(route)
        async with client(recorder) as ukc:
            with pytest.raises(MetroFanoutError) as caught:
                await ukc.instances.each(name="web").delete(missing_ok=True)
        assert caught.value.results == []
        assert [failure.metro for failure in caught.value.failures] == ["dal"]

    async def test_a_lookup_route_that_is_not_there_is_a_failure_not_an_absence(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/metros":
                return 200, envelope({"metros": METROS})
            return 404, {"status": "error", "message": "no such route"}

        recorder = routed(route)
        async with client(recorder) as ukc:
            # Every metro's listing is missing: that is not "no metro holds it".
            with pytest.raises(MetroFanoutError):
                await ukc.instances.get(name="ghost").delete(missing_ok=True)
            with pytest.raises(MetroFanoutError):
                await ukc.instances.each(name="ghost").delete(missing_ok=True)
        assert not [call for call in recorder.calls if call.method == "DELETE"]
