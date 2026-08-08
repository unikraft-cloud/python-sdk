# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The pieces the resource clients are built from: metros, references, patches,
# pagination, fan-out and handles.

from __future__ import annotations

import asyncio
import gc
import warnings
from collections.abc import AsyncIterator
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from unikraft_cloud import (
    REMOVE,
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
    MetroFulfilled,
    MetroRejected,
    fanout,
    fanout_settled,
)
from unikraft_cloud.core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from unikraft_cloud.core.handle_set import HandleSet
from unikraft_cloud.core.pagination import paginate
from unikraft_cloud.core.patch import to_patch_items
from unikraft_cloud.core.response import (
    as_ref,
    describe_ref,
    envelope_entries,
    or_absent,
    raise_for_envelope,
    require_first,
    to_query,
    to_refs,
    wire_ref,
)

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
    instances: list[dict[str, str]] | None = None


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
        assert to_patch_items({"tags": REMOVE}, "add") == [PatchItem("tags", "del", None)]

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


class TestPagination:
    async def test_follows_the_cursor_until_a_short_page(self) -> None:
        rows = [{"uuid": f"u{i}"} for i in range(25)]
        calls: list[tuple[int, str | None]] = []

        async def fetch(count: int, start: str | None) -> list[dict[str, str]]:
            calls.append((count, start))
            begin = (
                0
                if start is None
                else next(i for i, row in enumerate(rows) if row["uuid"] == start) + 1
            )
            return rows[begin : begin + count]

        got = await collect(paginate(fetch, lambda row: row["uuid"], 10))
        assert got == rows
        assert calls == [(10, None), (10, "u9"), (10, "u19")]

    async def test_defaults_to_a_hundred_per_page(self) -> None:
        calls: list[int] = []

        async def fetch(count: int, start: str | None) -> list[dict[str, str]]:
            calls.append(count)
            return [{"uuid": "u1"}]

        await collect(paginate(fetch, lambda row: row["uuid"]))
        assert calls == [100]

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

    def op(self, label: str) -> Handle:
        async def run(pinned: MetroTarget) -> str:
            self.log.append(f"{label}@{pinned.metro}")
            return f"{label}:{pinned.metro}"

        return Handle(self._chained(run), self.log)


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

    one = Handle(HandleSteps(locate=locate, fetch=fetch), log)
    if fail:

        def boom(label: str) -> Handle:
            async def run(pinned: MetroTarget) -> str:
                raise UnikraftCloudError(f"{pinned.metro} down", kind="http", status=503)

            return Handle(one._chained(run), log)

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

    async def test_counting_matches_warns_about_nothing(self) -> None:
        log: list[str] = []

        async def locate() -> list[Handle]:
            return [located(code, log) for code in ("fra", "dal")]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            assert await Set(locate).size() == 2
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
