# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Images: a per-metro listing merged across the scope, with the API's filters
# passed on as given.

from __future__ import annotations

from typing import Any

import httpx
import pytest

from unikraft_cloud import MetroFanoutError, UnikraftCloud

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
