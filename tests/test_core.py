# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The pieces the resource clients are built from: metros, references, patches,
# pagination, fan-out and handles.

from __future__ import annotations

import asyncio
import gc
import pickle
import warnings
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from unikraft_cloud import (
    REMOVE,
    AlreadyExistsError,
    ApiClientConfig,
    MetroEndpoint,
    MetroFanoutError,
    NotFoundError,
    PatchItem,
    Ref,
    ResourceEditor,
    UnikraftCloudError,
    collect,
    metro_base_url,
    metro_endpoint,
    with_metro,
)
from unikraft_cloud.core.fanout import (
    MetroFailure,
    MetroFulfilled,
    MetroRejected,
    fanout,
    fanout_settled,
)
from unikraft_cloud.core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from unikraft_cloud.core.handle_set import HandleSet
from unikraft_cloud.core.http import CallOptions
from unikraft_cloud.core.pagination import Listing, paginate
from unikraft_cloud.core.patch import to_patch_items
from unikraft_cloud.core.response import (
    as_ref,
    describe_ref,
    envelope_entries,
    matched_entries,
    or_absent,
    raise_for_envelope,
    require_first,
    to_query,
    to_refs,
    wire_ref,
)
from unikraft_cloud.core.session import Session, SessionConfig

from .conftest import envelope, metro, missing

FRA, DAL, SIN = (metro_endpoint(code) for code in ("fra", "dal", "sin"))


class TestMetroUrls:
    def test_builds_a_regional_url(self) -> None:
        assert metro_base_url("fra") == "https://api.fra.unikraft.cloud"

    def test_uses_a_full_url_verbatim(self) -> None:
        assert metro_base_url("https://api.staging.example.com") == (
            "https://api.staging.example.com"
        )

    def test_drops_a_trailing_slash(self) -> None:
        assert metro_base_url("https://api.staging.example.com/") == (
            "https://api.staging.example.com"
        )

    def test_drops_a_trailing_v1_the_operation_paths_already_carry(self) -> None:
        assert metro_base_url("https://api.staging.example.com/v1") == (
            "https://api.staging.example.com"
        )


def session(handler: Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]) -> Session:
    """A session whose control plane answers through `handler`."""
    platform = ApiClientConfig(
        base_url="https://api.fra.unikraft.cloud", transport=httpx.MockTransport(handler)
    )
    return Session(
        SessionConfig(
            platform=platform,
            control_plane=platform.with_base_url("https://controlplane.unikraft.cloud"),
            default_metro="fra",
        )
    )


class TestDiscovery:
    async def test_concurrent_callers_share_one_lookup(self) -> None:
        asked = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal asked
            asked += 1
            return httpx.Response(200, json=envelope({"metros": [metro("fra"), metro("dal")]}))

        shared = session(handler)
        first, second = await asyncio.gather(shared.discover(), shared.discover())
        assert [endpoint.metro for endpoint in first] == ["fra", "dal"]
        assert second == first
        assert asked == 1

    async def test_one_caller_giving_up_leaves_the_others_discovering(self) -> None:
        sent, release = asyncio.Event(), asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            sent.set()
            await release.wait()
            return httpx.Response(200, json=envelope({"metros": [metro("fra")]}))

        shared = session(handler)
        first = asyncio.ensure_future(shared.discover())
        second = asyncio.ensure_future(shared.discover())
        # Both are waiting on the one lookup before either gives up.
        await sent.wait()
        first.cancel()
        release.set()
        assert [endpoint.metro for endpoint in await second] == ["fra"]
        assert first.cancelled()


class Raw(BaseModel):
    model_config = ConfigDict(extra="allow")

    uuid: str
    name: str
    size: int | None = None


class Tagged(Raw):
    metro: str


class TestWithMetro:
    def test_tags_a_result_without_revalidating_it(self) -> None:
        raw = Raw.model_validate({"uuid": "u1", "name": "web"})
        tagged = with_metro(raw, "fra", Tagged)
        assert (tagged.metro, tagged.uuid, tagged.name, tagged.size) == ("fra", "u1", "web", None)

    def test_keeps_fields_the_specification_does_not_describe(self) -> None:
        raw = Raw.model_validate({"uuid": "u1", "name": "web", "surprise": 1})
        tagged = with_metro(raw, "fra", Tagged)
        assert tagged.model_extra == {"surprise": 1}

    def test_records_the_tag_as_set(self) -> None:
        raw = Raw.model_validate({"uuid": "u1", "name": "web"})
        assert with_metro(raw, "fra", Tagged).model_fields_set == {"uuid", "name", "metro"}

    def test_dumps_everything_it_carries(self) -> None:
        raw = Raw.model_validate({"uuid": "u1", "name": "web", "surprise": 1})
        assert with_metro(raw, "fra", Tagged).model_dump() == {
            "uuid": "u1",
            "name": "web",
            "size": None,
            "metro": "fra",
            "surprise": 1,
        }

    def test_narrows_the_tag_to_a_required_field(self) -> None:
        assert Tagged.model_fields["metro"].is_required()


class TestRefs:
    def test_needs_an_identifier(self) -> None:
        with pytest.raises(TypeError, match="needs either"):
            Ref()

    def test_takes_one_identifier_not_both(self) -> None:
        with pytest.raises(TypeError, match="not both"):
            Ref(uuid="u1", name="web")

    def test_rejects_an_unknown_key(self) -> None:
        with pytest.raises(TypeError, match="nope"):
            as_ref({"nope": "1"})

    def test_the_metro_never_reaches_the_wire(self) -> None:
        # It says where to send the request; the API rejects the unknown field.
        assert wire_ref(Ref(uuid="u1", metro="fra")) == {"uuid": "u1"}

    def test_filters_by_the_identifier_it_was_given(self) -> None:
        assert to_query(Ref(uuid="u1")) == {"uuid": ["u1"]}
        assert to_query(Ref(name="web")) == {"name": ["web"]}

    def test_describes_itself_for_an_error_message(self) -> None:
        assert describe_ref(Ref(name="web")) == 'name "web"'
        assert describe_ref(Ref(uuid="u1", metro="fra")) == 'uuid "u1" in fra'

    def test_normalises_one_or_many(self) -> None:
        assert to_refs(Ref(name="a")) == [Ref(name="a")]
        assert to_refs({"name": "a"}) == [Ref(name="a")]
        assert to_refs([{"uuid": "x"}, Ref(name="y")]) == [Ref(uuid="x"), Ref(name="y")]


class Err(BaseModel):
    status: int | None = None
    message: str | None = None


class Data(BaseModel):
    instances: list[dict[str, Any]] | None = None


class Res(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    message: str | None = None
    errors: list[Err] | None = None
    data: Data | None = None


class TestEnvelopes:
    def test_a_success_passes(self) -> None:
        raise_for_envelope(Res(status="success"))

    def test_only_error_counts_as_a_failure(self) -> None:
        # Autoscale answers "unconfigured", which is not a failure.
        raise_for_envelope(Res(status="unconfigured"))

    def test_reports_a_logical_error_inside_a_200(self) -> None:
        with pytest.raises(UnikraftCloudError, match="boom"):
            raise_for_envelope(Res(status="error", message="boom"))

    def test_a_partial_success_raises_and_carries_the_envelope(self) -> None:
        res = Res(status="partial_success", errors=[Err(status=403, message="denied")])
        with pytest.raises(UnikraftCloudError) as caught:
            raise_for_envelope(res)
        assert caught.value.status == 403
        assert caught.value.body is res

    def test_an_item_the_api_could_not_act_on_raises(self) -> None:
        # The envelope stays 200 and says what failed inside `data`.
        res = Res(
            status="error",
            message="Failed to perform all operations",
            data=Data(instances=[missing(name="ghost")]),
        )
        with pytest.raises(NotFoundError, match="No instance with name 'ghost'") as caught:
            raise_for_envelope(res, "instances")
        assert caught.value.status == 404

    def test_a_partly_failed_bulk_carries_what_did_succeed(self) -> None:
        res = Res(
            status="partial_success",
            message="Failed to perform all operations",
            data=Data(instances=[{"uuid": "u1", "status": "success"}, missing(name="ghost")]),
        )
        with pytest.raises(NotFoundError) as caught:
            raise_for_envelope(res, "instances")
        assert caught.value.results == [{"uuid": "u1", "status": "success"}]
        assert caught.value.errors is not None
        assert caught.value.errors[0].name == "ghost"

    def test_a_name_already_taken_is_its_own_error(self) -> None:
        taken = {
            "status": "error",
            "message": "An instance with the name 'web' already exists",
            "error": 23,
        }
        with pytest.raises(AlreadyExistsError) as caught:
            raise_for_envelope(Res(status="error", data=Data(instances=[taken])), "instances")
        assert caught.value.status == 409
        assert caught.value.errors is not None
        assert caught.value.errors[0].code == 23

    def test_a_failed_item_without_a_code_is_not_a_not_found(self) -> None:
        # A wait that timed out reports the instance with no error code.
        res = Res(
            status="error",
            message="Operation timed out",
            data=Data(instances=[{"uuid": "u1", "status": "error"}]),
        )
        with pytest.raises(UnikraftCloudError, match="Operation timed out") as caught:
            raise_for_envelope(res, "instances")
        assert not isinstance(caught.value, NotFoundError)

    def test_a_lookup_treats_the_references_it_missed_as_absences(self) -> None:
        res = Res(
            status="partial_success",
            data=Data(instances=[{"uuid": "u1"}, missing(name="ghost")]),
        )
        assert matched_entries(res, "instances") == [{"uuid": "u1"}]

    def test_a_lookup_that_found_nothing_is_no_failure(self) -> None:
        res = Res(status="error", data=Data(instances=[missing(name="ghost")]))
        assert matched_entries(res, "instances") == []

    def test_reads_a_payload_list(self) -> None:
        res = Res(status="success", data=Data(instances=[{"uuid": "a"}]))
        assert envelope_entries(res, "instances") == [{"uuid": "a"}]

    def test_an_absent_payload_is_an_empty_list(self) -> None:
        assert envelope_entries(Res(status="success"), "instances") == []

    def test_an_empty_list_is_a_not_found(self) -> None:
        with pytest.raises(NotFoundError, match='instance name "web" not found'):
            require_first([], 'instance name "web"')

    def test_returns_the_first_of_a_singleton_list(self) -> None:
        assert require_first([1, 2], "x") == 1


class TestOrAbsent:
    async def test_a_404_becomes_absence(self) -> None:
        async def missing() -> int:
            raise NotFoundError("gone", kind="http", status=404)

        assert await or_absent(missing()) is None

    async def test_any_other_failure_propagates(self) -> None:
        async def denied() -> int:
            raise UnikraftCloudError("no", kind="http", status=403)

        with pytest.raises(UnikraftCloudError):
            await or_absent(denied())

    async def test_a_result_passes_through(self) -> None:
        async def found() -> int:
            return 42

        assert await or_absent(found()) == 42


class TestPatches:
    def test_infers_the_operation_for_each_property(self) -> None:
        assert to_patch_items({"memory_mb": 512, "vcpus": 2}, "set") == [
            PatchItem("memory_mb", "set", 512),
            PatchItem("vcpus", "set", 2),
        ]

    def test_none_means_no_opinion_and_is_skipped(self) -> None:
        assert to_patch_items({"a": None, "b": 1}, "set") == [PatchItem("b", "set", 1)]

    def test_remove_clears_the_property_whatever_the_operation(self) -> None:
        # A `set` with no value is what clears a property: a bare `del` removes
        # nothing from a list or a map, and a scalar rejects it outright.
        assert to_patch_items({"tags": REMOVE}, "add") == [PatchItem("tags", "set", None)]

    def test_a_normaliser_rewrites_values_on_the_way_out(self) -> None:
        assert to_patch_items({"image": "nginx"}, "set", lambda prop, value: {"url": value}) == [
            PatchItem("image", "set", {"url": "nginx"})
        ]

    def test_a_staged_edit_keeps_the_order_it_was_written(self) -> None:
        sent: list[list[PatchItem]] = []

        def commit(items: list[PatchItem]) -> str:
            sent.append(items)
            return "applied"

        editor: ResourceEditor[str] = ResourceEditor(commit, "instance")
        editor.set(memory_mb=512).add(tags=["prod"]).delete(env=["OLD"]).apply()
        assert [(item.prop, item.op) for item in sent[0]] == [
            ("memory_mb", "set"),
            ("tags", "add"),
            ("env", "del"),
        ]

    def test_an_empty_edit_is_rejected(self) -> None:
        editor: ResourceEditor[str] = ResourceEditor(lambda items: "applied", "instance")
        with pytest.raises(TypeError, match="no changes to apply"):
            editor.apply()

    def test_an_edit_after_apply_does_not_leak_into_the_applied_one(self) -> None:
        sent: list[list[PatchItem]] = []

        def commit(items: list[PatchItem]) -> str:
            sent.append(items)
            return "applied"

        editor: ResourceEditor[str] = ResourceEditor(commit, "instance")
        editor.set(memory_mb=512).apply()
        # The commit may be lazy -- a handle sent when awaited -- so what it was
        # handed must be what was staged at the time.
        editor.add(tags=["late"])
        assert [item.prop for item in sent[0]] == ["memory_mb"]


def listing(
    rows: list[dict[str, str]], calls: list[tuple[int, str | None]]
) -> Callable[[int, str | None], Awaitable[list[dict[str, str]]]]:
    """A page fetcher with the API's own cursor, which includes the item it names."""

    async def fetch(count: int, start: str | None) -> list[dict[str, str]]:
        calls.append((count, start))
        begin = 0 if start is None else next(i for i, r in enumerate(rows) if r["uuid"] == start)
        return rows[begin : begin + count]

    return fetch


class TestPagination:
    async def test_follows_the_cursor_until_a_short_page(self) -> None:
        rows = [{"uuid": f"u{i}"} for i in range(25)]
        calls: list[tuple[int, str | None]] = []

        got = await collect(paginate(listing(rows, calls), lambda row: row["uuid"], 10))

        # Every item once: the page the cursor names starts with it again.
        assert got == rows
        assert calls == [(10, None), (11, "u9"), (11, "u19")]

    async def test_a_page_size_of_one_still_advances(self) -> None:
        rows = [{"uuid": f"u{i}"} for i in range(3)]
        calls: list[tuple[int, str | None]] = []

        got = await collect(paginate(listing(rows, calls), lambda row: row["uuid"], 1))

        assert got == rows

    async def test_defaults_to_a_hundred_per_page(self) -> None:
        calls: list[int] = []

        async def fetch(count: int, start: str | None) -> list[dict[str, str]]:
            calls.append(count)
            return [{"uuid": "u1"}]

        await collect(paginate(fetch, lambda row: row["uuid"]))
        assert calls == [100]

    async def test_reads_on_from_an_earlier_item_when_the_cursor_is_gone(self) -> None:
        rows = [{"uuid": f"u{i}"} for i in range(5)]
        live = list(rows)
        calls: list[tuple[int, str | None]] = []

        async def churning(count: int, start: str | None) -> list[dict[str, str]]:
            calls.append((count, start))
            if start is None:
                # The item this page ends on is deleted before the next request.
                page = live[:count]
                live.remove(page[-1])
                return page
            begin = next((i for i, row in enumerate(live) if row["uuid"] == start), None)
            # An unknown `from` is an empty page, which is how the API answers.
            return [] if begin is None else live[begin : begin + count]

        got = await collect(paginate(churning, lambda row: row["uuid"], 2))

        # Every item once, although the listing lost the item it was reading from.
        assert got == rows
        assert calls == [(2, None), (3, "u1"), (3, "u0"), (3, "u3")]

    async def test_a_page_size_of_one_resumes_from_the_page_before(self) -> None:
        rows = [{"uuid": f"u{i}"} for i in range(3)]
        live = list(rows)

        async def churning(count: int, start: str | None) -> list[dict[str, str]]:
            if start == "u1":
                live.remove(rows[1])
                return []
            begin = next((i for i, row in enumerate(live) if row["uuid"] == start), None)
            if start is None:
                begin = 0
            return [] if begin is None else live[begin : begin + count]

        # One item per page leaves no earlier item on the page to fall back to.
        assert await collect(paginate(churning, lambda row: row["uuid"], 1)) == rows

    async def test_a_listing_that_lost_every_item_it_read_says_so(self) -> None:
        async def vanished(count: int, start: str | None) -> list[dict[str, str]]:
            return [] if start else [{"uuid": "u0"}, {"uuid": "u1"}]

        with pytest.raises(UnikraftCloudError, match="lost its place"):
            await collect(paginate(vanished, lambda row: row["uuid"], 2))

    async def test_stops_when_there_is_no_usable_cursor(self) -> None:
        calls: list[int] = []

        async def fetch(count: int, start: str | None) -> list[dict[str, None]]:
            calls.append(count)
            return [{"uuid": None}] * count

        # A full page with no cursor would otherwise be requested forever.
        assert len(await collect(paginate(fetch, lambda row: row["uuid"], 2))) == 2
        assert calls == [2]


def pages(
    endpoint: MetroEndpoint, items: list[str], *, delay: float = 0.0, fail_after: int | None = None
) -> AsyncIterator[str]:
    async def generate() -> AsyncIterator[str]:
        for index, item in enumerate(items):
            if fail_after is not None and index == fail_after:
                raise UnikraftCloudError(f"{endpoint.metro} down", kind="http", status=503)
            await asyncio.sleep(delay)
            yield item

    return generate()


class TestListings:
    async def test_awaiting_one_reads_every_page(self) -> None:
        rows = [{"uuid": f"u{i}"} for i in range(3)]
        assert await Listing(paginate(listing(rows, []), lambda row: row["uuid"], 2)) == rows

    async def test_closing_one_releases_the_pages_it_did_not_read(self) -> None:
        closed: list[str] = []

        async def rows() -> AsyncIterator[dict[str, str]]:
            try:
                for index in range(5):
                    yield {"uuid": f"u{index}"}
            finally:
                closed.append("released")

        every = Listing(rows())
        async for _ in every:
            break
        await every.aclose()
        assert closed == ["released"]

    async def test_a_listing_read_as_a_context_manager_closes_itself(self) -> None:
        closed: list[str] = []

        async def rows() -> AsyncIterator[dict[str, str]]:
            try:
                for index in range(5):
                    yield {"uuid": f"u{index}"}
            finally:
                closed.append("released")

        async with Listing(rows()) as every:
            async for _ in every:
                break
        assert closed == ["released"]

    async def test_a_second_pass_says_the_listing_is_spent(self) -> None:
        rows = [{"uuid": "u1"}]
        every = Listing(paginate(listing(rows, []), lambda row: row["uuid"]))
        assert [row async for row in every] == rows
        with pytest.raises(RuntimeError, match="already been read"):
            await every


class TestErrors:
    def test_survives_a_pickle_round_trip(self) -> None:
        error = NotFoundError("gone", kind="http", status=404, body={"status": "error"})
        error.results = ["kept"]

        back = pickle.loads(pickle.dumps(error))

        assert isinstance(back, NotFoundError)
        assert (str(back), back.kind, back.status, back.body) == (
            "gone",
            "http",
            404,
            {"status": "error"},
        )
        assert back.results == ["kept"]

    def test_a_fan_out_failure_survives_one_too(self) -> None:
        failure = MetroFailure(metro="fra", error=NotFoundError("gone", kind="http"))
        back = pickle.loads(pickle.dumps(MetroFanoutError("1 of 2 metros failed", [failure])))

        assert isinstance(back, MetroFanoutError)
        assert [(f.metro, str(f.error)) for f in back.failures] == [("fra", "gone")]


class TestFanout:
    async def test_yields_in_arrival_order_not_metro_order(self) -> None:
        def each(endpoint: MetroEndpoint) -> AsyncIterator[str]:
            slow = endpoint.metro == "fra"
            return pages(
                endpoint,
                [f"{endpoint.metro}{i}" for i in range(3)],
                delay=0.03 if slow else 0.01,
            )

        got = [item async for item in fanout([FRA, DAL], each)]
        assert sorted(got) == ["dal0", "dal1", "dal2", "fra0", "fra1", "fra2"]
        # The fast metro finishes first, so a slow one never holds it up.
        assert got.index("dal2") < got.index("fra2")

    async def test_a_single_metro_raises_its_own_error(self) -> None:
        def each(endpoint: MetroEndpoint) -> AsyncIterator[str]:
            return pages(endpoint, ["a"], fail_after=0)

        with pytest.raises(UnikraftCloudError) as caught:
            [item async for item in fanout([FRA], each)]
        assert not isinstance(caught.value, MetroFanoutError)
        assert caught.value.status == 503

    async def test_drains_the_healthy_metros_before_raising(self) -> None:
        def each(endpoint: MetroEndpoint) -> AsyncIterator[str]:
            if endpoint.metro == "sin":
                return pages(endpoint, ["sin0"], fail_after=0)
            return pages(endpoint, [f"{endpoint.metro}{i}" for i in range(2)])

        got: list[str] = []
        with pytest.raises(MetroFanoutError) as caught:
            async for item in fanout([FRA, DAL, SIN], each):
                got.append(item)
        assert sorted(got) == ["dal0", "dal1", "fra0", "fra1"]
        assert [failure.metro for failure in caught.value.failures] == ["sin"]
        assert caught.value.status == 503

    async def test_keeps_what_arrived_before_a_metro_failed(self) -> None:
        def each(endpoint: MetroEndpoint) -> AsyncIterator[str]:
            if endpoint.metro == "sin":
                return pages(endpoint, ["sin0", "sin1"], fail_after=1)
            return pages(endpoint, ["fra0"])

        got: list[str] = []
        with pytest.raises(MetroFanoutError):
            async for item in fanout([FRA, SIN], each):
                got.append(item)
        assert sorted(got) == ["fra0", "sin0"]

    async def test_breaking_early_releases_every_metro(self) -> None:
        closed: list[str] = []

        def each(endpoint: MetroEndpoint) -> AsyncIterator[str]:
            async def generate() -> AsyncIterator[str]:
                try:
                    for index in range(50):
                        await asyncio.sleep(0.001)
                        yield f"{endpoint.metro}{index}"
                finally:
                    closed.append(endpoint.metro)

            return generate()

        seen = 0
        async for _ in fanout([FRA, DAL, SIN], each):
            seen += 1
            if seen == 3:
                break
        await asyncio.sleep(0.05)
        assert set(closed) == {"fra", "dal", "sin"}

    async def test_breaking_early_raises_nothing_even_after_a_failure(self) -> None:
        def each(endpoint: MetroEndpoint) -> AsyncIterator[str]:
            if endpoint.metro == "sin":
                return pages(endpoint, ["sin0"], fail_after=0)
            return pages(endpoint, [f"{endpoint.metro}{i}" for i in range(20)], delay=0.001)

        seen = 0
        async for _ in fanout([FRA, DAL, SIN], each):
            seen += 1
            if seen == 2:
                break

    async def test_collapses_one_shared_status_onto_the_aggregate(self) -> None:
        def each(endpoint: MetroEndpoint) -> AsyncIterator[str]:
            return pages(endpoint, ["x"], fail_after=0)

        with pytest.raises(MetroFanoutError) as caught:
            [item async for item in fanout([FRA, DAL], each)]
        assert len(caught.value.failures) == 2
        assert caught.value.status == 503


class TestFanoutSettled:
    async def test_reports_every_outcome(self) -> None:
        async def each(endpoint: MetroEndpoint) -> str:
            if endpoint.metro == "sin":
                raise UnikraftCloudError("nope", kind="http", status=500)
            return endpoint.metro.upper()

        outcomes = await fanout_settled([FRA, SIN], each)
        assert isinstance(outcomes[0], MetroFulfilled)
        assert outcomes[0].ok and outcomes[0].value == "FRA"
        assert isinstance(outcomes[1], MetroRejected)
        assert not outcomes[1].ok
        assert outcomes[1].endpoint.metro == "sin"


def target(metro: str = "fra", name: str = "web") -> MetroTarget:
    return MetroTarget(
        metro=metro, base_url=f"https://api.{metro}.unikraft.cloud", ref=Ref(name=name)
    )


class Handle(ResourceHandle[Any]):
    """A handle that records what it did, standing in for a resource's own."""

    def __init__(self, steps: HandleSteps[Any], log: list[str]) -> None:
        super().__init__(steps)
        self.log = log

    def op(self, label: str, **opts: Any) -> Handle:
        async def run(pinned: MetroTarget) -> str:
            self.log.append(f"{label}@{pinned.metro}")
            return f"{label}:{pinned.metro}"

        return Handle(self._chained(run, self._options(**opts)), self.log)


def handle(log: list[str], *, value: str | None = None) -> Handle:
    async def locate() -> Located[Any]:
        log.append("locate")
        return Located(target=target(), value=value)

    async def fetch(pinned: MetroTarget) -> str:
        log.append("fetch")
        return "read"

    return Handle(HandleSteps(locate=locate, fetch=fetch, what='instance name "web"'), log)


class TestHandles:
    async def test_awaiting_one_yields_the_resource(self) -> None:
        log: list[str] = []
        assert await handle(log) == "read"
        assert log == ["locate", "fetch"]

    async def test_each_step_runs_at_most_once(self) -> None:
        log: list[str] = []
        one = handle(log)
        assert await one == "read"
        assert await one == "read"
        assert log == ["locate", "fetch"]

    async def test_awaiting_one_twice_at_once_still_runs_each_step_once(self) -> None:
        log: list[str] = []
        one = handle(log)
        first, second = await asyncio.gather(one, one)
        assert first == second == "read"
        assert log == ["locate", "fetch"]

    async def test_a_located_value_is_not_read_again(self) -> None:
        log: list[str] = []
        assert await handle(log, value="carried") == "carried"
        assert log == ["locate"]

    async def test_an_operation_costs_no_read(self) -> None:
        log: list[str] = []
        assert await handle(log).op("suspend") == "suspend:fra"
        assert log == ["locate", "suspend@fra"]

    async def test_chained_operations_run_in_order(self) -> None:
        log: list[str] = []
        await handle(log).op("suspend").op("wait").op("logs")
        assert log == ["locate", "suspend@fra", "wait@fra", "logs@fra"]

    async def test_reports_which_metro_it_resolved_to(self) -> None:
        assert await handle([]).where() == "fra"

    async def test_one_waiter_giving_up_leaves_the_others_reading(self) -> None:
        log: list[str] = []
        started, release = asyncio.Event(), asyncio.Event()

        async def locate() -> Located[Any]:
            started.set()
            await release.wait()
            log.append("locate")
            return Located(target=target(), value="read")

        async def fetch(pinned: MetroTarget) -> str:
            return "read"

        one = Handle(HandleSteps(locate=locate, fetch=fetch, what="instance"), log)
        first = asyncio.ensure_future(one.where())
        second = asyncio.ensure_future(one.where())
        # Both are waiting on the one lookup before either gives up.
        await started.wait()
        first.cancel()
        release.set()
        assert await second == "fra"
        assert first.cancelled()
        assert log == ["locate"]

    async def test_dropping_one_un_awaited_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            handle([])
            gc.collect()
        messages = [str(w.message) for w in caught if w.category is RuntimeWarning]
        assert messages and "never awaited" in messages[0]
        assert 'instance name "web"' in messages[0]

    async def test_an_awaited_chain_warns_about_nothing(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            chained = handle([]).op("suspend").op("wait")
            await chained
            del chained
            gc.collect()
        assert not [w for w in caught if w.category is RuntimeWarning]

    async def test_a_dropped_chain_warns_once_not_per_link(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            handle([]).op("suspend").op("wait")
            gc.collect()
        assert len([w for w in caught if w.category is RuntimeWarning]) == 1


class Set(HandleSet[Handle, str]):
    async def suspend(self) -> list[str]:
        return await self._map(lambda one: one.op("suspend"))


def located(metro: str, log: list[str], *, fail: bool = False) -> Handle:
    async def locate() -> Located[Any]:
        return Located(target=target(metro=metro), value=f"{metro}-instance")

    async def fetch(pinned: MetroTarget) -> str:
        return f"{pinned.metro}-read"

    one = Handle(HandleSteps(locate=locate, fetch=fetch, located=True), log)
    if fail:

        def boom(label: str, **opts: Any) -> Handle:
            async def run(pinned: MetroTarget) -> str:
                raise UnikraftCloudError(f"{pinned.metro} down", kind="http", status=503)

            return Handle(one._chained(run, CallOptions()), log)

        one.op = boom  # type: ignore[method-assign]
    return one


class TestHandleSets:
    async def test_reports_size_and_metros_in_handle_order(self) -> None:
        log: list[str] = []

        async def locate() -> list[Handle]:
            return [located(code, log) for code in ("fra", "dal", "sin")]

        both = Set(locate)
        assert await both.size() == 3
        assert await both.where() == ["fra", "dal", "sin"]

    async def test_awaiting_reads_every_match(self) -> None:
        log: list[str] = []

        async def locate() -> list[Handle]:
            return [located(code, log) for code in ("fra", "dal")]

        assert await Set(locate) == ["fra-instance", "dal-instance"]

    async def test_one_operation_giving_up_leaves_the_others_reading(self) -> None:
        log: list[str] = []
        started, release = asyncio.Event(), asyncio.Event()

        async def locate() -> list[Handle]:
            started.set()
            await release.wait()
            return [located(code, log) for code in ("fra", "dal")]

        both = Set(locate)
        first = asyncio.ensure_future(both.size())
        second = asyncio.ensure_future(both.where())
        await started.wait()
        first.cancel()
        release.set()
        assert await second == ["fra", "dal"]
        assert first.cancelled()

    async def test_counting_matches_warns_about_nothing(self) -> None:
        log: list[str] = []

        async def locate() -> list[Handle]:
            return [located(code, log) for code in ("fra", "dal")]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            assert await Set(locate).size() == 2
            gc.collect()
        assert not [w for w in caught if w.category is RuntimeWarning]

    async def test_handing_out_matches_warns_about_nothing_either(self) -> None:
        log: list[str] = []

        async def locate() -> list[Handle]:
            return [located(code, log) for code in ("fra", "dal")]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            handles = await Set(locate).handles()
            assert len(handles) == 2
            del handles
            gc.collect()
        assert not [w for w in caught if w.category is RuntimeWarning]

    async def test_a_partial_failure_keeps_the_successes(self) -> None:
        log: list[str] = []

        async def locate() -> list[Handle]:
            return [
                located("fra", log),
                located("dal", log),
                located("sin", log, fail=True),
            ]

        with pytest.raises(MetroFanoutError) as caught:
            await Set(locate).suspend()
        assert caught.value.results == ["suspend:fra", "suspend:dal"]
        assert [failure.metro for failure in caught.value.failures] == ["sin"]
        assert caught.value.status == 503
