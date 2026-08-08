# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import Any

import httpx
import pytest

from unikraft_cloud.api.platform import models

__all__ = [
    "Recorder",
    "certificate",
    "changed_instance",
    "envelope",
    "instance",
    "instance_logs",
    "metro",
    "queued",
    "quotas",
    "routed",
    "service_group",
    "volume",
]


@pytest.fixture(autouse=True)
def _no_ambient_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a developer's real environment out of the tests.

    The client falls back to `UKC_TOKEN` and `UKC_METRO`, and a real `UKC_METRO`
    would pin the scope and change what most of these tests exercise.
    """
    monkeypatch.delenv("UKC_TOKEN", raising=False)
    monkeypatch.delenv("UKC_METRO", raising=False)


class Recorder:
    """A transport that records every request it was asked to send."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.calls: list[httpx.Request] = []
        self.transport = httpx.MockTransport(self._send)
        self._handler = handler

    def _send(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return self._handler(request)

    @property
    def urls(self) -> list[str]:
        return [str(call.url) for call in self.calls]

    @property
    def paths(self) -> list[str]:
        return [call.url.path for call in self.calls]

    def to(self, path: str) -> list[httpx.Request]:
        """Every recorded request for one path."""
        return [call for call in self.calls if call.url.path == path]

    def metros(self, path: str) -> list[str]:
        """The metros a path was requested from, e.g. `api.fra....` -> `fra`."""
        return [metro_of(call) for call in self.to(path)]


def metro_of(request: httpx.Request) -> str:
    """The metro a request went to: `api.fra.unikraft.cloud` -> `fra`."""
    return request.url.host.split(".")[1]


def envelope(data: Any = None, *, status: str = "success", **extra: Any) -> dict[str, Any]:
    """The response envelope every operation answers with."""
    body: dict[str, Any] = {"status": status, "op_time_us": 1, **extra}
    if data is not None:
        body["data"] = data
    return body


def queued(pages: Sequence[tuple[int, Any]]) -> Recorder:
    """A transport answering with queued responses, repeating the last one."""
    remaining = list(pages)
    index = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        page = remaining[min(index[0], len(remaining) - 1)]
        index[0] += 1
        return httpx.Response(page[0], json=page[1])

    return Recorder(handler)


def routed(route: Callable[[httpx.Request], tuple[int, Any]]) -> Recorder:
    """A transport answering per request.

    Metro fan-out runs concurrently, so responses cannot be queued in a fixed
    order -- they are routed instead.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        status, body = route(request)
        return httpx.Response(status, json=body)

    return Recorder(handler)


def instance(uuid: str = "u1", name: str = "web", **overrides: Any) -> dict[str, Any]:
    """An instance, carrying every field the specification requires."""
    return {
        "uuid": uuid,
        "name": name,
        "created_at": "2026-01-01T00:00:00Z",
        "state": "running",
        "image": "nginx:latest",
        "memory_mb": 256,
        "vcpus": 1,
        "restart_policy": "never",
        **overrides,
    }


def changed_instance(uuid: str = "u1", name: str = "web", **overrides: Any) -> dict[str, Any]:
    """What a start, stop, suspend or delete reports back."""
    return {
        "status": "success",
        "uuid": uuid,
        "name": name,
        "state": "stopped",
        "previous_state": "running",
        **overrides,
    }


def instance_logs(uuid: str = "u1", name: str = "web", output: str = "aGk=") -> dict[str, Any]:
    """A console log as the API reports it, output base64-encoded."""
    span = {"start": 0, "end": 1}
    return {
        "uuid": uuid,
        "name": name,
        "output": output,
        "available": span,
        "range": span,
        "state": "running",
    }


def volume(uuid: str = "v1", name: str = "data", **overrides: Any) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "name": name,
        "created_at": "2026-01-01T00:00:00Z",
        "state": "available",
        "size_mb": 1024,
        "persistent": True,
        "quota_policy": "static",
        **overrides,
    }


def service_group(uuid: str = "s1", name: str = "web", **overrides: Any) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "name": name,
        "created_at": "2026-01-01T00:00:00Z",
        "persistent": True,
        "autoscale": False,
        "soft_limit": 1,
        "hard_limit": 2,
        **overrides,
    }


def certificate(uuid: str = "c1", name: str = "tls", **overrides: Any) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "name": name,
        "created_at": "2026-01-01T00:00:00Z",
        "common_name": "example.com",
        "state": "valid",
        **overrides,
    }


def quotas(uuid: str = "q1", **overrides: Any) -> dict[str, Any]:
    """Quotas with every required field, read off the generated models.

    The shape is broad and entirely uninteresting to the tests, so it is derived
    rather than written out.
    """
    stats = {name: 0 for name, f in models.QuotasStats.model_fields.items() if f.is_required()}
    limits = {name: 0 for name, f in models.QuotasLimits.model_fields.items() if f.is_required()}
    return {"uuid": uuid, "used": stats, "hard": stats, "limits": limits, **overrides}


def metro(code: str, *, name: str | None = None) -> dict[str, Any]:
    """One metro as the control plane reports it.

    The code comes back upper-case and the endpoint carries the `/v1` prefix the
    operation paths already have, which is what the SDK has to normalise.
    """
    return {
        "uuid": f"m-{code}",
        "endpoint": f"https://api.{code}.unikraft.cloud/v1",
        "name": name or code.title(),
        "iata_code": code.upper(),
        "country": "de",
    }


@pytest.fixture
def metros() -> Iterator[list[dict[str, Any]]]:
    yield [metro("fra"), metro("dal")]
