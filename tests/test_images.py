# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Images: a per-metro listing merged across the scope, with the API's filters
# passed on as given.

from __future__ import annotations

from typing import Any

import httpx
import pytest

from unikraft_cloud import MetroFanoutError, NotFoundError, UnikraftCloud, UnikraftCloudError

from .conftest import Recorder, envelope, image, metro, metro_of, routed


def registry(**per_metro: list[dict[str, Any]]) -> Recorder:
    """A transport whose image listing differs per metro; a missing metro fails."""

    def route(request: httpx.Request) -> tuple[int, Any]:
        if request.url.path == "/v1/metros":
            return 200, envelope({"metros": [metro("fra"), metro("dal")]})
        if request.url.path == "/v1/images":
            code = metro_of(request)
            if code not in per_metro:
                return 500, {"status": "error", "message": f"{code} is down"}
            return 200, envelope({"images": per_metro[code]})
        return 404, {"status": "error", "message": f"no route for {request.url.path}"}

    return routed(route)


class TestImages:
    async def test_lists_one_metro_tagged(self) -> None:
        recorder = registry(fra=[image()])
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            found = await ukc.images.list()
        assert [(i.metro, i.url, i.size_in_bytes) for i in found] == [
            ("fra", "index.unikraft.io/org/app:latest", 4096)
        ]
        assert recorder.paths == ["/v1/images"]

    async def test_passes_the_filters_on_as_query_parameters(self) -> None:
        recorder = registry(fra=[])
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            await ukc.images.list(tag="org/app:latest", digest="sha256:abc")
        params = recorder.calls[0].url.params
        assert (params["tag"], params["digest"]) == ("org/app:latest", "sha256:abc")

    async def test_sends_no_filter_it_was_not_given(self) -> None:
        recorder = registry(fra=[])
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            await ukc.images.list()
        assert str(recorder.calls[0].url.params) == ""

    async def test_merges_every_metro_in_scope(self) -> None:
        recorder = registry(
            fra=[image("index.unikraft.io/org/app:latest")],
            dal=[image("index.unikraft.io/org/other:v2")],
        )
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            found = await ukc.images.list()
        assert sorted((i.metro, i.url) for i in found) == [
            ("dal", "index.unikraft.io/org/other:v2"),
            ("fra", "index.unikraft.io/org/app:latest"),
        ]

    async def test_a_metro_that_fails_reports_the_rest(self) -> None:
        recorder = registry(fra=[image()])
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            with pytest.raises(MetroFanoutError) as caught:
                await ukc.images.list()
        assert [f.metro for f in caught.value.failures] == ["dal"]
        assert [i.metro for i in caught.value.results] == ["fra"]

    async def test_keeps_the_raw_escape_hatch(self) -> None:
        recorder = registry(fra=[image()])
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            res = await ukc.images.api.get_images()
        assert res.data is not None and res.data.images is not None
        assert res.data.images[0].url == "index.unikraft.io/org/app:latest"


CONTROL_PLANE = "controlplane.unikraft.cloud"


def control_plane(*images: dict[str, Any]) -> Recorder:
    """A transport whose control plane lists these images for any namespace."""

    def route(request: httpx.Request) -> tuple[int, Any]:
        if request.url.host == CONTROL_PLANE and request.url.path == "/v1/images":
            return 200, envelope({"images": list(images)})
        return 404, {"status": "error", "message": f"no route for {request.url}"}

    return routed(route)


def registry_image(name: str = "org/app", *tags: str, digest: str = "sha256:abc") -> dict[str, Any]:
    """An image as the control plane reports it, with details."""
    return {
        "name": name,
        "tags": [
            {"name": tag, "digest": digest, "size": 4096, "push_time": "2026-01-01T00:00:00Z"}
            for tag in (tags or ("latest",))
        ],
    }


class TestRegistry:
    async def test_find_asks_the_control_plane_about_the_namespace(self) -> None:
        recorder = control_plane(registry_image("org/app", "1.2.3", "latest"))
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            found = await ukc.images.find("org/app:1.2.3")
        assert found is not None
        assert (found.repository, found.tag, found.digest, found.size) == (
            "org/app",
            "1.2.3",
            "sha256:abc",
            4096,
        )
        assert found.reference == "org/app:1.2.3"
        assert found.push_time is not None and found.push_time.year == 2026
        sent = recorder.calls[0]
        assert sent.url.host == CONTROL_PLANE
        assert (sent.url.params["details"], sent.url.params["namespace"]) == ("true", "org")
        assert sent.headers["authorization"] == "Bearer tok"

    async def test_a_missing_tag_is_none(self) -> None:
        recorder = control_plane(registry_image("org/app", "latest"), registry_image("org/other"))
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            assert await ukc.images.find("org/app:1.2.3") is None
            assert await ukc.images.find("org/nothing:latest") is None
            assert await ukc.images.exists("org/app") is True
            assert await ukc.images.exists("org/app:1.2.3") is False

    async def test_find_takes_a_digest_a_registry_host_and_a_scheme(self) -> None:
        recorder = control_plane(registry_image("org/app", "1.2.3", digest="sha256:ABC"))
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            by_digest = await ukc.images.find("org/app@sha256:abc")
            by_host = await ukc.images.find("unikraft.io/org/app:1.2.3")
            by_port = await ukc.images.find("oci://localhost:5000/org/app:1.2.3")
        assert by_digest is not None and by_digest.tag == "1.2.3"
        assert by_host is not None and by_port is not None
        assert all(call.url.params["namespace"] == "org" for call in recorder.calls)

    async def test_a_bare_name_is_an_official_image_as_the_cli_has_it(self) -> None:
        recorder = control_plane(registry_image("official/nginx", "latest"))
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            found = await ukc.images.find("nginx")
        assert found is not None and found.reference == "official/nginx:latest"
        assert recorder.calls[0].url.params["namespace"] == "official"

    async def test_localhost_is_a_registry_host_and_a_namespace_may_nest(self) -> None:
        recorder = control_plane(registry_image("org/sub/app", "v1"))
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            nested = await ukc.images.find("org/sub/app:v1")
            hosted = await ukc.images.find("localhost/org/sub/app:v1")
        assert nested is not None and nested.repository == "org/sub/app"
        assert hosted is not None
        assert all(call.url.params["namespace"] == "org" for call in recorder.calls)

    async def test_a_tag_and_a_digest_together_must_both_match(self) -> None:
        recorder = control_plane(registry_image("org/app", "v1", "v2", digest="sha256:abc"))
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            assert await ukc.images.exists("org/app:v2@sha256:abc") is True
            assert await ukc.images.exists("org/app:v2@sha256:def") is False
            assert await ukc.images.exists("org/app:v3@sha256:abc") is False

    async def test_an_empty_or_malformed_tag_is_refused(self) -> None:
        recorder = control_plane()
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            with pytest.raises(ValueError, match="tag"):
                await ukc.images.find("org/app:")
            with pytest.raises(ValueError, match="tag"):
                await ukc.images.find("org/app:v1:v2")
        assert recorder.calls == []

    async def test_a_malformed_reference_is_refused_before_anything_is_sent(self) -> None:
        recorder = control_plane()
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            with pytest.raises(ValueError, match="digest"):
                await ukc.images.find("org/app@sha256")
            with pytest.raises(ValueError, match="digest"):
                await ukc.images.find("org/app@")
            with pytest.raises(ValueError, match="names an image"):
                await ukc.images.find("org/")
        assert recorder.calls == []

    async def test_a_namespace_the_registry_does_not_have_holds_no_image(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            return 200, envelope({"images": []})

        recorder = routed(route)
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            assert await ukc.images.find("nobody/app:latest") is None

    async def test_a_control_plane_route_that_is_not_there_is_a_failure(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            return 404, {"status": "error", "message": "no such route"}

        recorder = routed(route)
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            with pytest.raises(NotFoundError):
                await ukc.images.find("org/app:latest")

    async def test_a_control_plane_failure_is_a_failure(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            return 503, {"status": "error", "message": "registry unavailable"}

        recorder = routed(route)
        async with UnikraftCloud(token="tok", metro="fra", transport=recorder.transport) as ukc:
            with pytest.raises(UnikraftCloudError, match="registry unavailable"):
                await ukc.images.exists("org/app")
