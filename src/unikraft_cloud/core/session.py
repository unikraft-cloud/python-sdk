# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The transport and metro knowledge shared by every resource client: one set of
# credentials, one memoised metro discovery, and the rules for turning a metro
# scope into concrete endpoints.

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from ..api.controlplane.metros_gen import MetrosApi
from .errors import UnikraftCloudError
from .http import ApiClientConfig
from .metro import (
    Metro,
    MetroEndpoint,
    MetroScope,
    metro_base_url,
    metro_endpoint,
    same_metro,
)
from .response import envelope_entries

__all__ = ["Session", "SessionConfig"]


@dataclass(frozen=True)
class SessionConfig:
    """How a :class:`Session` was configured."""

    #: Transport config for the platform API; its base URL is the default metro.
    platform: ApiClientConfig
    #: Transport config for the global control-plane API.
    control_plane: ApiClientConfig
    #: The metro used for operations that must pick exactly one (e.g. `create`).
    default_metro: Metro
    #: Set when the caller named a metro. A scope covering several metros says
    #: nothing about where to create, so this stays the target for the
    #: operations that must pick one.
    named_metro: Metro | None = None
    #: Set when the caller named an explicit endpoint (a base URL, or a metro
    #: that is already a URL). Every scope then resolves to just that endpoint:
    #: there is nothing to discover, and fanning out would invent hostnames the
    #: caller never mentioned.
    pinned: MetroEndpoint | None = None


class Session:
    """Shared state behind one client: credentials, discovery and its cache.

    Scoped clients (``ukc.metro("fra")``) reuse the same session, so discovery
    and connections are shared rather than duplicated.
    """

    def __init__(self, config: SessionConfig) -> None:
        #: Platform transport config; its base URL points at the default metro.
        self.platform = config.platform
        #: Control-plane transport config (the control plane is global).
        self.control_plane = config.control_plane
        #: The single endpoint every scope collapses to, when one was named.
        self.pinned = config.pinned
        #: The metro named for this client, the target of an operation that must
        #: pick one when the scope covers several.
        self.named_metro = config.named_metro
        #: The endpoint the raw API surfaces point at: the pinned one, or the
        #: metro named at construction.
        self.default_endpoint = config.pinned or MetroEndpoint(
            metro=config.default_metro,
            base_url=config.platform.base_url,
        )
        self._metros: MetrosApi | None = None
        self._discovery: asyncio.Future[list[MetroEndpoint]] | None = None

    async def discover(self) -> list[MetroEndpoint]:
        """Every metro this account can reach, asked of the control plane once.

        The answer is cached for the client's lifetime, and shared by concurrent
        callers. A failed discovery is not cached, so a transient control-plane
        outage does not poison the client.
        """
        if self.pinned is not None:
            return [self.pinned]
        if self._discovery is None:
            discovery = asyncio.ensure_future(self._list_metros())
            self._discovery = discovery

            def forget_if_failed(task: asyncio.Future[list[MetroEndpoint]]) -> None:
                failed = task.cancelled() or task.exception() is not None
                if failed and self._discovery is discovery:
                    self._discovery = None

            discovery.add_done_callback(forget_if_failed)
        # Shielded: the task is shared, so one caller giving up on it must not
        # cancel the discovery every other caller is waiting on.
        return await asyncio.shield(self._discovery)

    async def _list_metros(self) -> list[MetroEndpoint]:
        if self._metros is None:
            self._metros = MetrosApi(self.control_plane)

        try:
            metros = envelope_entries(await self._metros.list_metros(), "metros")
        except UnikraftCloudError as cause:
            # A rejected token keeps its type and status. Naming metros is the
            # advice for a control plane that could not answer, not for a refusal.
            if cause.status in (401, 403):
                raise
            raise UnikraftCloudError(
                "Could not discover the available metros from the control plane. "
                'Name the metros you want (`UnikraftCloud(metro="fra")`, '
                '`ukc.metro("fra")`, or `metros=[...]`) to skip discovery.',
                kind="fanout",
                status=cause.status,
            ) from cause
        except Exception as cause:
            raise UnikraftCloudError(
                "Could not discover the available metros from the control plane. "
                'Name the metros you want (`UnikraftCloud(metro="fra")`, '
                '`ukc.metro("fra")`, or `metros=[...]`) to skip discovery.',
                kind="fanout",
            ) from cause

        endpoints: list[MetroEndpoint] = []
        for metro in metros:
            # Prefer the IATA code as the identity users type; fall back to the
            # name. Lower-cased because the control plane reports codes upper-case
            # while `ukc.metro("fra")` is how they are written, and a result should
            # be tagged the same whether it was reached by discovery or by name.
            code = (metro.iata_code or metro.name or "").lower()
            if not code:
                continue
            # The control plane reports each metro's own endpoint; trust it over a
            # URL built from the code, so new or relocated metros just work.
            endpoints.append(
                MetroEndpoint(metro=code, base_url=metro_base_url(metro.endpoint or code))
            )

        if not endpoints:
            raise UnikraftCloudError(
                "The control plane reported no metros for this account, "
                "so there is nothing to query.",
                kind="fanout",
            )
        return endpoints

    def endpoint_for(self, metro: Metro) -> MetroEndpoint:
        """The endpoint serving a metro the caller named.

        A pinned client has one endpoint only, so naming any other metro raises
        rather than quietly reaching the pinned one.
        """
        if self.pinned is None:
            return metro_endpoint(metro)
        if same_metro(metro, self.pinned):
            return self.pinned
        raise UnikraftCloudError(
            f"This client is pinned to {self.pinned.metro}, so it cannot reach "
            f"{metro}. Build another client for it, or drop `base_url`/a URL "
            "`metro` to talk to every metro the account can reach.",
            kind="fanout",
        )

    async def resolve(self, scope: MetroScope) -> list[MetroEndpoint]:
        """Turn a scope into the endpoints to call.

        An explicit scope never triggers discovery -- naming metros is also how
        you avoid the extra request. A metro named twice is called once.
        """
        if scope == "all":
            return await self.discover()

        codes = [scope] if isinstance(scope, str) else list(scope)
        if not codes:
            raise UnikraftCloudError(
                'An empty metro scope selects no metros; pass "all" or at least one metro.',
                kind="fanout",
            )
        endpoints: dict[str, MetroEndpoint] = {}
        for code in codes:
            endpoint = self.endpoint_for(code)
            endpoints.setdefault(endpoint.base_url, endpoint)
        return list(endpoints.values())

    async def resolve_one(self, scope: MetroScope, operation: str) -> MetroEndpoint:
        """Resolve a scope that must name exactly one metro.

        Creating a resource, or a bulk operation on references that were never
        located, needs a single target. A scope covering several metros names
        none, so the metro named for the client is used; without one, it asks
        rather than picking one.
        """
        if scope == "all" and self.pinned is not None:
            return self.pinned
        endpoints = [] if scope == "all" else await self.resolve(scope)
        if len(endpoints) == 1:
            return endpoints[0]
        if self.named_metro is not None:
            return self.endpoint_for(self.named_metro)
        if scope == "all":
            raise UnikraftCloudError(
                f"{operation} targets a single metro, but this client covers every metro "
                'the account can reach. Name one with `ukc.metro("fra")`, `metros="fra"`, '
                'or `UnikraftCloud(metro="fra")`.',
                kind="fanout",
            )
        raise UnikraftCloudError(
            f"{operation} targets a single metro, but the current scope spans "
            f"{len(endpoints)} ({_names(endpoints)}). Pick one with "
            f'`ukc.metro("{endpoints[0].metro}")` or `metros="{endpoints[0].metro}"`.',
            kind="fanout",
        )


def _names(endpoints: Sequence[MetroEndpoint]) -> str:
    return ", ".join(endpoint.metro for endpoint in endpoints)
