# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The resources beside instances: volumes, service groups, certificates and
# quotas.

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from unikraft_cloud import Ref, UnikraftCloud

from .conftest import (
    Recorder,
    certificate,
    envelope,
    metro,
    metro_of,
    quotas,
    routed,
    service_group,
    volume,
)


def platform(**payloads: Any) -> Recorder:
    """A transport answering each resource's endpoints with a fixed payload."""

    def route(request: httpx.Request) -> tuple[int, Any]:
        path = request.url.path
        if path == "/v1/metros":
            return 200, envelope({"metros": [metro("fra"), metro("dal")]})
        if request.url.params.get("from"):
            return 200, envelope({key: [] for key in payloads})
        for key, rows in payloads.items():
            if path.startswith(f"/v1/{_prefix(key)}"):
                return 200, envelope({key: rows})
        return 404, {"status": "error", "message": f"no route for {path}"}

    return routed(route)


def _prefix(key: str) -> str:
    return {"service_groups": "services", "quotas": "users"}.get(key, key)


def client(recorder: Recorder, **config: Any) -> UnikraftCloud:
    return UnikraftCloud(token="tok", metro="fra", transport=recorder.transport, **config)


class TestVolumes:
    async def test_reads_one_tagged_with_its_metro(self) -> None:
        recorder = platform(volumes=[volume()])
        async with client(recorder) as ukc:
            found = await ukc.volumes.get(name="data")
        assert (found.metro, found.name, found.size_mb) == ("fra", "data", 1024)

    async def test_lists_them(self) -> None:
        recorder = platform(volumes=[volume()])
        async with client(recorder) as ukc:
            assert [vol.name async for vol in ukc.volumes.list()] == ["data"]

    async def test_attaches_to_an_instance_by_name(self) -> None:
        recorder = platform(volumes=[volume(status="success")])
        async with client(recorder) as ukc:
            await ukc.volumes.get(name="data").attach(to="web", at="/data")
        assert json.loads(recorder.calls[-1].content) == [
            {"attach_to": {"name": "web"}, "at": "/data", "name": "data"}
        ]

    async def test_attaches_to_an_instance_by_uuid(self) -> None:
        recorder = platform(volumes=[volume(status="success")])
        async with client(recorder) as ukc:
            await ukc.volumes.get(name="data").attach(to=Ref(uuid="u9"), at="/data", readonly=True)
        assert json.loads(recorder.calls[-1].content) == [
            {"attach_to": {"uuid": "u9"}, "at": "/data", "readonly": True, "name": "data"}
        ]

    async def test_detaches_under_the_wire_name(self) -> None:
        recorder = platform(volumes=[volume(status="success")])
        async with client(recorder) as ukc:
            await ukc.volumes.get(name="data").detach(from_="web")
        # `from` is a Python keyword, so the field is renamed and aliased back.
        assert json.loads(recorder.calls[-1].content) == [{"from": {"name": "web"}, "name": "data"}]

    async def test_updates_properties(self) -> None:
        recorder = platform(volumes=[volume(status="success")])
        async with client(recorder) as ukc:
            await ukc.volumes.get(name="data").update(size_mb=2048)
        assert json.loads(recorder.calls[-1].content) == [
            {"name": "data", "prop": "size_mb", "op": "set", "value": 2048}
        ]

    async def test_deletes_in_bulk(self) -> None:
        recorder = platform(volumes=[volume(status="success")])
        async with client(recorder) as ukc:
            await ukc.volumes.delete([{"name": "data"}, {"uuid": "v2"}])
        assert json.loads(recorder.calls[-1].content) == [{"name": "data"}, {"uuid": "v2"}]


class TestServiceGroups:
    async def test_reads_one_tagged_with_its_metro(self) -> None:
        recorder = platform(service_groups=[service_group()])
        async with client(recorder) as ukc:
            found = await ukc.services.get(name="web")
        assert (found.metro, found.name, found.hard_limit) == ("fra", "web", 2)

    async def test_lists_them(self) -> None:
        recorder = platform(service_groups=[service_group()])
        async with client(recorder) as ukc:
            assert [group.name async for group in ukc.services.list()] == ["web"]

    async def test_updates_properties(self) -> None:
        recorder = platform(service_groups=[service_group(status="success")])
        async with client(recorder) as ukc:
            await ukc.services.get(name="web").update(hard_limit=10)
        assert json.loads(recorder.calls[-1].content) == [
            {"name": "web", "prop": "hard_limit", "op": "set", "value": 10}
        ]

    async def test_applies_a_staged_edit(self) -> None:
        recorder = platform(service_groups=[service_group(status="success")])
        async with client(recorder) as ukc:
            await ukc.services.get(name="web").edit().set(soft_limit=1).add(domains=["a"]).apply()
        assert [item["op"] for item in json.loads(recorder.calls[-1].content)] == ["set", "add"]


class TestCertificates:
    async def test_reads_one_tagged_with_its_metro(self) -> None:
        recorder = platform(certificates=[certificate()])
        async with client(recorder) as ukc:
            found = await ukc.certificates.get(name="tls")
        assert (found.metro, found.common_name, found.state) == ("fra", "example.com", "valid")

    async def test_lists_them(self) -> None:
        recorder = platform(certificates=[certificate()])
        async with client(recorder) as ukc:
            assert [cert.name async for cert in ukc.certificates.list()] == ["tls"]

    async def test_replaces_the_material_as_a_whole(self) -> None:
        recorder = platform(certificates=[certificate()])
        async with client(recorder) as ukc:
            await ukc.certificates.get(name="tls").update(chain="PEM", pkey="KEY")
        assert json.loads(recorder.calls[-1].content) == [
            {"name": "tls", "chain": "PEM", "pkey": "KEY"}
        ]

    async def test_deletes_in_bulk(self) -> None:
        recorder = platform(certificates=[certificate(status="success")])
        async with client(recorder) as ukc:
            await ukc.certificates.delete({"name": "tls"})
        assert json.loads(recorder.calls[-1].content) == [{"name": "tls"}]


class TestQuotas:
    async def test_reads_one_metros_quotas(self) -> None:
        recorder = platform(quotas=[quotas()])
        async with client(recorder) as ukc:
            found = await ukc.users.quotas()
        assert [(quota.metro, quota.uuid) for quota in found] == [("fra", "q1")]

    async def test_merges_every_metro_in_scope(self) -> None:
        recorder = platform(quotas=[quotas()])
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            found = await ukc.users.quotas()
        assert sorted(quota.metro for quota in found) == ["dal", "fra"]

    async def test_keeps_what_arrived_when_a_metro_fails(self) -> None:
        def route(request: httpx.Request) -> tuple[int, Any]:
            if request.url.path == "/v1/metros":
                return 200, envelope({"metros": [metro("fra"), metro("dal")]})
            if metro_of(request) == "dal":
                return 503, {"status": "error", "message": "down"}
            return 200, envelope({"quotas": [quotas()]})

        recorder = routed(route)
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            with pytest.raises(Exception) as caught:
                await ukc.users.quotas()
        results = getattr(caught.value, "results", [])
        assert [quota.metro for quota in results] == ["fra"]


class TestEveryResourceIsOnEveryScope:
    @pytest.mark.parametrize(
        "attribute", ["instances", "volumes", "services", "certificates", "users"]
    )
    async def test_reachable_account_wide_and_per_metro(self, attribute: str) -> None:
        recorder = platform(volumes=[volume()])
        async with UnikraftCloud(token="tok", transport=recorder.transport) as ukc:
            assert hasattr(ukc, attribute)
            assert hasattr(ukc.metro("fra"), attribute)
            assert hasattr(ukc.metros(["fra"]), attribute)
