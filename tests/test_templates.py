# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Instance templates: preparing one from a specification, cloning instances
# out of it, and the reads and deletes around them.

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from unikraft_cloud import MetroFanoutError, NotFoundError, UnikraftCloud

from .conftest import (
    Recorder,
    changed_instance,
    envelope,
    instance,
    metro,
    metro_of,
    missing,
    routed,
)


def template(uuid: str = "t1", name: str = "worker", **overrides: Any) -> dict[str, Any]:
    """A template as the API reports it: an instance in the ``template`` state."""
    return instance(uuid=uuid, name=name, state="template", **overrides)


#: A lookup miss as the API reports it: the item named, with its not-found code.
absent = missing(name="worker", noun="instance template")


def platform(*, templates: list[dict[str, Any]] | None = None, prepared: bool = True) -> Recorder:
    """A transport that answers the instance and template endpoints.

    The templates are listed from the start, or, with ``prepared`` false, only
    once a clone has asked for one to be prepared, as the platform has it.
    """
    pending = [] if prepared else list(templates or [])
    rows = list(templates or []) if prepared else []

    def route(request: httpx.Request) -> tuple[int, Any]:
        path = request.url.path
        if path == "/v1/metros":
            return 200, envelope({"metros": [metro("fra"), metro("dal")]})
        if request.url.params.get("from"):
            return 200, envelope({"instances": []})
        if path == "/v1/instances/templates":
            if request.method == "DELETE":
                body = json.loads(request.content)
                return 200, envelope(
                    {"instances": [changed_instance(name=item.get("name")) for item in body]}
                )
            names = request.url.params.get_list("name")
            found = [row for row in rows if not names or row["name"] in names]
            return 200, envelope({"instances": found})
        if path == "/v1/instances" and request.method == "POST":
            body = json.loads(request.content)
            if isinstance(body.get("template"), dict) and body["template"].get("prepare"):
                rows.extend(pending)
                pending.clear()
            return 200, envelope(
                {
                    "instances": [
                        {"uuid": "u-new", "name": body.get("name", "made"), "state": "stopped"}
                    ]
                }
            )
        if path == "/v1/instances" and request.method == "DELETE":
            return 200, envelope({"instances": [changed_instance(uuid="u-new")]})
        if path == "/v1/instances" and request.method == "GET":
            return 200, envelope({"instances": [instance(uuid="u-new", name="made")]})
        return 404, {"status": "error", "message": f"no route for {path}"}

    return routed(route)


def client(recorder: Recorder, **config: Any) -> UnikraftCloud:
    return UnikraftCloud(token="tok", metro="fra", transport=recorder.transport, **config)


class TestPrepare:
    async def test_prepares_through_a_stopped_clone_it_deletes_again(self) -> None:
        recorder = platform(templates=[template()], prepared=False)
        async with client(recorder) as ukc:
            made = await ukc.templates.prepare(
                "worker",
                create_args={"image": "org/worker:v1", "memory_mb": 1024, "tags": ["app=web"]},
                autokill_ms=60_000,
                prepare_timeout_seconds=120,
            )
        assert (made.metro, made.name, made.state) == ("fra", "worker", "template")
        # A read says the template is not there yet; the seed clone is removed
        # only once the template is listed.
        assert [(call.method, call.url.path) for call in recorder.calls] == [
            ("GET", "/v1/instances/templates"),
            ("POST", "/v1/instances"),
            ("GET", "/v1/instances/templates"),
            ("DELETE", "/v1/instances"),
        ]
        # The seed clone carries the whole template specification and never runs.
        assert json.loads(recorder.calls[1].content) == {
            "template": {
                "name": "worker",
                "prepare": True,
                "create_args": {"image": "org/worker:v1", "memory_mb": 1024, "tags": ["app=web"]},
                "autokill": {"time_ms": 60000},
                "prepare_timeout_s": 120,
            },
            "autostart": False,
            "tags": ["app=web"],
        }
        assert recorder.calls[2].url.params.get_list("name") == ["worker"]
        assert json.loads(recorder.calls[3].content) == [{"uuid": "u-new"}]

    async def test_a_template_that_exists_is_read_and_nothing_is_seeded(self) -> None:
        recorder = platform(templates=[template()])
        async with client(recorder) as ukc:
            made = await ukc.templates.prepare("worker", create_args={"image": "org/worker:v1"})
        assert (made.metro, made.name) == ("fra", "worker")
        assert [(call.method, call.url.path) for call in recorder.calls] == [
            ("GET", "/v1/instances/templates")
        ]

    async def test_the_seed_create_outlasts_the_preparation_timeout(self) -> None:
        recorder = platform(templates=[template()], prepared=False)
        async with client(recorder, timeout=5.0) as ukc:
            await ukc.templates.prepare(
                "worker", create_args={"image": "org/worker:v1"}, prepare_timeout_seconds=120
            )
        create = next(call for call in recorder.calls if call.method == "POST")
        assert create.extensions["timeout"]["read"] == 130
        # The reads around it keep the client's own timeout.
        assert recorder.calls[0].extensions["timeout"]["read"] == 5.0

    async def test_without_a_preparation_timeout_the_seed_create_is_not_cut_short(self) -> None:
        recorder = platform(templates=[template()], prepared=False)
        async with client(recorder, timeout=5.0) as ukc:
            await ukc.templates.prepare("worker", create_args={"image": "org/worker:v1"})
        create = next(call for call in recorder.calls if call.method == "POST")
        # The platform bounds the preparation itself; the client does not guess at it.
        assert create.extensions["timeout"]["read"] is None

    async def test_looks_for_the_template_where_the_seed_would_go(self) -> None:
        listed = {"fra": [], "dal": [template(uuid="t-dal")]}
        seeded: list[str] = []

        def route(request: httpx.Request) -> tuple[int, Any]:
            path, where = request.url.path, metro_of(request)
            if path == "/v1/metros":
                return 200, envelope({"metros": [metro("fra"), metro("dal")]})
            if request.url.params.get("from"):
                return 200, envelope({"instances": []})
            if path == "/v1/instances/templates":
                return 200, envelope({"instances": listed[where]})
            if path == "/v1/instances" and request.method == "POST":
                seeded.append(where)
                listed[where].append(template(uuid=f"t-{where}"))
                return 200, envelope({"instances": [{"uuid": "u-new", "state": "stopped"}]})
            if path == "/v1/instances" and request.method == "DELETE":
                return 200, envelope({"instances": [changed_instance(uuid="u-new")]})
            return 404, {"status": "error", "message": f"no route for {path}"}

        recorder = routed(route)
        # The client covers both metros but names fra, which is where a clone of
        # the template would be made: the one dal lists is not it.
        async with UnikraftCloud(
            token="tok", metro="fra", metros="all", transport=recorder.transport
        ) as ukc:
            made = await ukc.templates.prepare("worker", create_args={"image": "org/worker:v1"})
        assert (made.metro, made.uuid) == ("fra", "t-fra")
        assert seeded == ["fra"]
        assert set(recorder.metros("/v1/instances/templates")) == {"fra"}

    async def test_waits_for_a_template_the_platform_lists_a_moment_later(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unikraft_cloud.resources import templates as module

        slept: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(module, "_sleep", fake_sleep)
        reads = 0

        def route(request: httpx.Request) -> tuple[int, Any]:
            nonlocal reads
            if request.url.path == "/v1/instances/templates":
                reads += 1
                # The first read is the check before seeding; two more lag.
                if reads < 4:
                    return 200, envelope({"instances": [absent]}, status="error")
                return 200, envelope({"instances": [template()]})
            if request.method == "POST":
                return 200, envelope({"instances": [{"uuid": "u-new", "state": "stopped"}]})
            return 200, envelope({"instances": [changed_instance(uuid="u-new")]})

        recorder = routed(route)
        async with client(recorder) as ukc:
            made = await ukc.templates.prepare("worker", create_args={"image": "org/w:v1"})
        assert made.name == "worker"
        assert slept == [0.5, 1.0]
        assert [call.method for call in recorder.calls] == [
            "GET",
            "POST",
            "GET",
            "GET",
            "GET",
            "DELETE",
        ]

    async def test_gives_up_on_a_template_that_never_appears(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unikraft_cloud.resources import templates as module

        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(module, "_sleep", fake_sleep)

        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/instances/templates":
                return 200, envelope({"instances": [absent]}, status="error")
            return 200, envelope({"instances": [{"uuid": "u-new", "state": "stopped"}]})

        recorder = routed(route)
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError):
                await ukc.templates.prepare(
                    "worker", create_args={"image": "org/w:v1"}, prepare_timeout_seconds=1
                )
        # The seed clone is left for the caller to inspect; nothing was deleted.
        assert not [call for call in recorder.calls if call.method == "DELETE"]

    async def test_rejects_a_source_property_the_api_does_not_have(self) -> None:
        recorder = platform()
        async with client(recorder) as ukc:
            with pytest.raises(TypeError, match="memroy_mb"):
                await ukc.templates.prepare("worker", create_args={"memroy_mb": 512})
        assert recorder.calls == []

    async def test_a_preparation_the_platform_bounds_is_still_awaited(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unikraft_cloud.resources import templates as module

        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(module, "_sleep", fake_sleep)
        reads = 0

        def route(request: httpx.Request) -> tuple[int, Any]:
            nonlocal reads
            if request.url.path == "/v1/instances/templates":
                reads += 1
                if reads < 3:
                    return 200, envelope({"instances": [absent]}, status="error")
                return 200, envelope({"instances": [template()]})
            if request.method == "POST":
                return 200, envelope({"instances": [{"uuid": "u-new", "state": "stopped"}]})
            return 200, envelope({"instances": [changed_instance(uuid="u-new")]})

        recorder = routed(route)
        async with client(recorder) as ukc:
            made = await ukc.templates.prepare(
                "worker", create_args={"image": "org/w:v1"}, prepare_timeout_seconds=-1
            )
        # -1 leaves the bound to the platform; the SDK still polls, then removes the seed.
        assert made.name == "worker"
        assert [call.method for call in recorder.calls] == ["GET", "POST", "GET", "GET", "DELETE"]

    async def test_each_poll_is_bounded_by_what_is_left_of_the_deadline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unikraft_cloud.resources import templates as module

        async def fake_sleep(seconds: float) -> None:
            pass

        monkeypatch.setattr(module, "_sleep", fake_sleep)
        reads = 0

        def route(request: httpx.Request) -> tuple[int, Any]:
            nonlocal reads
            if request.url.path == "/v1/instances/templates":
                reads += 1
                if reads < 3:
                    return 200, envelope({"instances": [absent]}, status="error")
                return 200, envelope({"instances": [template()]})
            if request.method == "POST":
                return 200, envelope({"instances": [{"uuid": "u-new", "state": "stopped"}]})
            return 200, envelope({"instances": [changed_instance(uuid="u-new")]})

        recorder = routed(route)
        async with client(recorder) as ukc:
            await ukc.templates.prepare(
                "worker", create_args={"image": "org/w:v1"}, prepare_timeout_seconds=30
            )
        listings = [c for c in recorder.calls if c.url.path == "/v1/instances/templates"]
        # The check before seeding keeps the client's own timeout; the polls cannot
        # outlive the deadline, however the client was configured.
        assert listings[0].extensions["timeout"]["read"] is None
        assert all(0 < c.extensions["timeout"]["read"] <= 30 for c in listings[1:])

    async def test_a_listing_route_that_is_not_there_is_not_polled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unikraft_cloud.resources import templates as module

        slept: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(module, "_sleep", fake_sleep)
        reads = 0

        def route(request: httpx.Request) -> tuple[int, Any]:
            nonlocal reads
            if request.url.path == "/v1/instances/templates":
                reads += 1
                if reads == 1:
                    return 200, envelope({"instances": [absent]}, status="error")
                return 404, {"status": "error", "message": "no such route"}
            return 200, envelope({"instances": [{"uuid": "u-new", "state": "stopped"}]})

        recorder = routed(route)
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError):
                await ukc.templates.prepare("worker", create_args={"image": "org/w:v1"})
        assert [call.method for call in recorder.calls] == ["GET", "POST", "GET"]
        assert slept == []


class TestClone:
    async def test_clones_with_the_template_reference_and_the_clones_own_properties(self) -> None:
        recorder = platform(templates=[template()])
        async with client(recorder) as ukc:
            made = await ukc.templates.get(name="worker").clone(
                name="job-1",
                roms=[
                    {"name": "job", "at": "/mnt/job", "files": [{"path": "job.json", "data": "{}"}]}
                ],
                volumes=[{"size_mb": 64, "at": "/tmp"}],
                features=["delete-on-stop"],
                annotations={"app/role": "worker"},
            )
        assert made.uuid == "u-new"
        posts = [call for call in recorder.calls if call.method == "POST"]
        assert [call.url.path for call in posts] == ["/v1/instances"]
        assert json.loads(posts[0].content) == {
            "template": {"name": "worker"},
            "name": "job-1",
            "roms": [
                {"name": "job", "at": "/mnt/job", "files": [{"path": "job.json", "data": "{}"}]}
            ],
            "volumes": [{"size_mb": 64, "at": "/tmp"}],
            "features": ["delete-on-stop"],
            "annotations": {"app/role": "worker"},
        }

    async def test_a_pinned_scope_clones_without_looking_the_template_up(self) -> None:
        recorder = platform(templates=[template()])
        async with client(recorder) as ukc:
            target = await ukc.templates.get(name="worker").clone(name="job-2").resolve()
        assert target.ref.uuid == "u-new"
        assert [call.method for call in recorder.calls] == ["POST"]

    async def test_a_misspelled_property_is_refused_when_clone_is_called(self) -> None:
        recorder = platform(templates=[template()])
        async with client(recorder) as ukc:
            with pytest.raises(TypeError, match="memroy_mb"):
                ukc.templates.get(name="worker").clone(memroy_mb=512)
        assert recorder.calls == []

    async def test_refuses_to_override_what_the_template_settles(self) -> None:
        recorder = platform(templates=[template()])
        async with client(recorder) as ukc:
            with pytest.raises(TypeError, match="image"):
                ukc.templates.get(name="worker").clone(image="other:latest")
            with pytest.raises(TypeError, match="template"):
                ukc.templates.get(name="worker").clone(template={"name": "x"})
        assert recorder.calls == []

    async def test_clones_where_discovery_found_the_template(self) -> None:
        # The control plane reports dal at an endpoint the code would not rebuild.
        elsewhere = "https://dal.example.net"
        metros = [metro("fra"), {**metro("dal"), "endpoint": f"{elsewhere}/v1"}]

        def route(request: httpx.Request) -> tuple[int, Any]:
            path, host = request.url.path, request.url.host
            if path == "/v1/metros":
                return 200, envelope({"metros": metros})
            if request.url.params.get("from"):
                return 200, envelope({"instances": []})
            if path == "/v1/instances/templates":
                rows = [template()] if host == "dal.example.net" else []
                return 200, envelope({"instances": rows})
            if path == "/v1/instances" and request.method == "POST":
                return 200, envelope({"instances": [{"uuid": "u-new", "name": "job"}]})
            return 200, envelope({"instances": [instance(uuid="u-new", name="job")]})

        recorder = routed(route)
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            clone = await ukc.templates.get(name="worker").clone(name="job")
        posts = [call for call in recorder.calls if call.method == "POST"]
        assert [call.url.host for call in posts] == ["dal.example.net"]
        assert (clone.metro, clone.uuid) == ("dal", "u-new")

    async def test_a_metro_without_the_template_answers_as_the_api_does(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            path = request.url.path
            if path == "/v1/metros":
                return 200, envelope({"metros": [metro("fra"), metro("dal")]})
            if request.url.params.get("from"):
                return 200, envelope({"instances": []})
            if path == "/v1/instances/templates":
                if metro_of(request) == "dal":
                    return 200, envelope({"instances": [template()]})
                # The miss is an error item inside a 200, which is no failure of fra.
                return 200, envelope({"instances": [absent]}, status="error")
            return 404, {"status": "error", "message": f"no route for {path}"}

        recorder = routed(route)
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            found = await ukc.templates.get(name="worker")
        assert (found.metro, found.name) == ("dal", "worker")


class TestReadsAndDeletes:
    async def test_reads_one_tagged_with_its_metro(self) -> None:
        recorder = platform(templates=[template()])
        async with client(recorder) as ukc:
            found = await ukc.templates.get(name="worker")
        assert (found.metro, found.name, found.state) == ("fra", "worker", "template")
        assert recorder.calls[-1].url.path == "/v1/instances/templates"
        assert recorder.calls[-1].url.params.get("details") == "true"

    async def test_lists_them(self) -> None:
        recorder = platform(templates=[template(), template(uuid="t2", name="api")])
        async with client(recorder) as ukc:
            assert [tpl.name async for tpl in ukc.templates.list()] == ["worker", "api"]

    async def test_deletes_by_name_through_the_templates_endpoint(self) -> None:
        recorder = platform(templates=[template()])
        async with client(recorder) as ukc:
            await ukc.templates.get(name="worker").delete()
        assert recorder.calls[-1].method == "DELETE"
        assert recorder.calls[-1].url.path == "/v1/instances/templates"
        assert json.loads(recorder.calls[-1].content) == [{"name": "worker"}]

    async def test_a_missing_template_can_be_ignored_on_delete(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            # As the API answers: the item named, with its not-found code.
            return 200, envelope(
                {"instances": [missing(name="gone", noun="instance template")]},
                status="error",
                message="Failed to perform all operations",
            )

        recorder = routed(route)
        async with client(recorder) as ukc:
            assert await ukc.templates.get(name="gone").delete(missing_ok=True) is None

    async def test_each_by_tag_deletes_every_match(self) -> None:
        recorder = platform(templates=[template(), template(uuid="t2", name="api")])
        async with client(recorder) as ukc:
            deleted = await ukc.templates.each(tags=["app=web"]).delete()
        assert len(deleted) == 2
        listing = next(call for call in recorder.calls if call.method == "GET")
        assert listing.url.params.get("tags") == "app=web"


class TestInstanceSpec:
    async def test_a_template_based_instance_spec_passes_the_check_and_travels_verbatim(
        self,
    ) -> None:
        spec: dict[str, Any] = {
            "name": "web",
            "template": {"name": "worker", "prepare": True, "create_args": {"image": "org/w:v1"}},
            "roms": [{"name": "job", "at": "/mnt/job", "files": [{"path": "a", "data": "b"}]}],
            "volumes": [{"size_mb": 512, "at": "/tmp"}],
            "schedules": [{"name": "tick", "when": "*-*-* *:*:00/30", "action": "start"}],
            "features": ["delete-on-stop"],
            "annotations": {"app/role": "worker"},
            "autostart": False,
        }
        recorder = platform()
        async with client(recorder) as ukc:
            target = await ukc.instances.create(**spec).resolve()
        assert target.ref.uuid == "u-new"
        assert json.loads(recorder.calls[0].content) == spec


def tagged_platform(per_metro: Callable[[str], list[dict[str, Any]] | None]) -> Recorder:
    """A two-metro platform whose template listings differ per metro.

    ``per_metro`` returns the templates a metro lists, or ``None`` for a metro
    that is down. Deletes answer for what they were sent.
    """

    def route(request: httpx.Request) -> tuple[int, Any]:
        path = request.url.path
        if path == "/v1/metros":
            return 200, envelope({"metros": [metro("fra"), metro("dal")]})
        where = metro_of(request)
        rows = per_metro(where)
        if rows is None:
            return 500, {"status": "error", "message": f"{where} is down"}
        if path == "/v1/instances/templates" and request.method == "DELETE":
            sent = json.loads(request.content)
            gone = [
                changed_instance(
                    uuid=item.get("uuid", f"{item.get('name')}-uuid"), name=item.get("name")
                )
                for item in sent
            ]
            return 200, envelope({"instances": gone})
        if path == "/v1/instances/templates":
            names = request.url.params.get_list("name")
            found = [row for row in rows if not names or row["name"] in names]
            return 200, envelope({"instances": [] if request.url.params.get("from") else found})
        return 404, {"status": "error", "message": f"no route for {path}"}

    return routed(route)


class TestSets:
    async def test_each_by_tag_asks_every_metro_at_once(self) -> None:
        recorder = tagged_platform(lambda where: [template(f"{where}-1", f"{where}-worker")])
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            deleted = await ukc.templates.each(tags=["app=web"]).delete()
        assert sorted((item.metro, item.uuid) for item in deleted) == [
            ("dal", "dal-1"),
            ("fra", "fra-1"),
        ]
        listings = [
            call
            for call in recorder.calls
            if call.method == "GET"
            and call.url.path == "/v1/instances/templates"
            and not call.url.params.get("from")
        ]
        assert sorted(metro_of(call) for call in listings) == ["dal", "fra"]
        assert all(call.url.params["tags"] == "app=web" for call in listings)

    async def test_a_metro_that_fails_reports_the_templates_that_did_arrive(self) -> None:
        recorder = tagged_platform(lambda where: [template("fra-1")] if where == "fra" else None)
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            with pytest.raises(MetroFanoutError) as caught:
                await ukc.templates.each(tags=["app=web"]).delete()
        assert [failure.metro for failure in caught.value.failures] == ["dal"]
        assert [(tpl.metro, tpl.uuid) for tpl in caught.value.results] == [("fra", "fra-1")]

    async def test_a_set_of_a_missing_name_deletes_nothing_when_told_so(self) -> None:
        recorder = tagged_platform(lambda where: [])
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            assert await ukc.templates.each(name="ghost").delete(missing_ok=True) == []
            with pytest.raises(NotFoundError):
                await ukc.templates.each(name="ghost").delete()
        assert not [call for call in recorder.calls if call.method == "DELETE"]

    async def test_a_lookup_route_that_is_not_there_is_raised_at_once(self) -> None:
        recorder = routed(lambda request: (404, {"status": "error", "message": "no such route"}))
        async with client(recorder) as ukc:
            with pytest.raises(NotFoundError) as caught:
                await ukc.templates.each(tags=["batch"]).delete(missing_ok=True)
        assert not caught.value.absent
        assert [call.method for call in recorder.calls] == ["GET"]

    async def test_each_by_name_refreshes_every_match(self) -> None:
        recorder = tagged_platform(lambda where: [template(f"{where}-1", "worker")])
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            found = await ukc.templates.each(name="worker").refresh()
        assert sorted((tpl.metro, tpl.uuid) for tpl in found) == [
            ("dal", "dal-1"),
            ("fra", "fra-1"),
        ]

    async def test_a_bulk_delete_goes_through_the_templates_endpoint(self) -> None:
        recorder = tagged_platform(lambda where: [template("t1", "a"), template("t2", "b")])
        async with client(recorder) as ukc:
            deleted = await ukc.templates.delete([{"uuid": "t1"}, "b"])
        assert [item.uuid for item in deleted] == ["t1", "b-uuid"]
        sent = [json.loads(call.content) for call in recorder.calls if call.method == "DELETE"]
        assert sent == [[{"uuid": "t1"}, {"name": "b"}]]
