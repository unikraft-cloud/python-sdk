# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

import os
from collections.abc import Mapping
from types import TracebackType

import httpx
from typing_extensions import Self

from .api import Api
from .core.http import DEFAULT_TIMEOUT, ApiClientConfig
from .core.metro import (
    CONTROLPLANE_BASE_URL,
    DEFAULT_METRO,
    Metro,
    MetroEndpoint,
    MetroScope,
    is_url,
    metro_base_url,
)
from .core.session import Session, SessionConfig
from .resources.instances import Instances

__all__ = ["MetroClient", "Scope", "UnikraftCloud"]

#: Sent with every request, so the API can tell this SDK's traffic apart.
USER_AGENT = "unikraft-cloud-python"


class Scope:
    """The idiomatic resource clients for one metro scope.

    Every operation on these covers the scope: reads fan out and are merged, and
    each result carries the metro it came from.
    """

    def __init__(self, session: Session, scope: MetroScope) -> None:
        #: Which metros these clients cover.
        self.scope = scope
        #: Instances (microVMs).
        self.instances = Instances(session, scope)
        self._session = session


class MetroClient(Scope):
    """The resource clients for exactly one metro.

    Because the metro is known, single-resource operations need no lookup:
    ``get(name="web").suspend()`` is one request.
    """

    def __init__(self, session: Session, endpoint: MetroEndpoint) -> None:
        super().__init__(session, endpoint.metro)
        #: The metro these clients are pinned to.
        self.endpoint = endpoint
        #: The raw API surfaces, with the platform API pinned to this metro.
        self.api = Api(session.platform.with_base_url(endpoint.base_url), session.control_plane)


class UnikraftCloud(Scope):
    """The Unikraft Cloud SDK entry point.

    By default the client is account-wide: reads cover every metro the account can
    reach and are merged into one stream, with each result tagged by metro. Narrow
    that whenever you already know where a resource lives -- with :meth:`metro`,
    ``metros=`` on a call, or ``metro``/``metros`` here -- which also skips metro
    discovery.

    The raw, spec-shaped API stays available on :attr:`api`, and from
    ``unikraft_cloud.api.platform`` and ``unikraft_cloud.api.controlplane``.

    The client owns a connection pool, so close it when you are done -- either with
    ``async with`` or by awaiting :meth:`aclose`.

    .. code-block:: python

        from unikraft_cloud import UnikraftCloud

        async with UnikraftCloud() as ukc:  # token from UKC_TOKEN
            # Every metro, merged as the pages arrive.
            async for inst in ukc.instances.list(details=True):
                print(inst.metro, inst.name, inst.state)

            # One metro, one request per operation.
            await ukc.metro("fra").instances.get(name="web").suspend()
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        metro: Metro | None = None,
        metros: MetroScope | None = None,
        base_url: str | None = None,
        control_plane_url: str | None = None,
        headers: Mapping[str, str] | None = None,
        user_agent: str | None = None,
        http: httpx.AsyncClient | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        trust_env: bool = True,
        timeout: float | httpx.Timeout | None = DEFAULT_TIMEOUT,
    ) -> None:
        """Build a client.

        :param token: Bearer token. Falls back to the ``UKC_TOKEN`` environment
            variable.
        :param metro: Pin to a single metro (``"fra"``), or to a full
            ``http(s)://`` base URL for a staging or self-hosted deployment (used
            verbatim). Falls back to ``UKC_METRO``. When omitted, operations cover
            **every** metro the account can reach.
        :param metros: The metros operations cover by default: ``"all"``, one
            metro, or a list. Takes precedence over `metro`, which then only
            remains the target for operations that must pick a single metro.
        :param base_url: Explicit platform API base URL; overrides `metro`.
        :param control_plane_url: Override the control-plane API base URL.
        :param headers: Extra headers sent with every request.
        :param user_agent: Override the default User-Agent.
        :param http: An httpx client to send through. Supplying one makes its
            lifetime yours: :meth:`aclose` will not close it.
        :param transport: A transport to build the client around, chiefly for
            testing with ``httpx.MockTransport``.
        :param trust_env: Honour ``HTTP_PROXY``/``HTTPS_PROXY``/``NO_PROXY``.
        :param timeout: Timeout applied to every request. The default bounds
            connecting but not reading, because the platform API's ``wait``
            operations block for as long as they were asked to.
        """
        env_metro = os.environ.get("UKC_METRO")
        chosen_metro = metro or env_metro

        # A named base URL -- explicitly, or as the metro -- is the only endpoint
        # there is: nothing to discover, and no hostnames to invent.
        explicit_url = base_url or (chosen_metro if chosen_metro and is_url(chosen_metro) else None)
        default_metro = chosen_metro or DEFAULT_METRO
        resolved = metro_base_url(explicit_url or default_metro)

        # One httpx client for the whole session, so every resource client shares
        # its connection pool and there is a single thing to close.
        self._owns_http = http is None
        self._http = http or httpx.AsyncClient(
            transport=transport, trust_env=trust_env, timeout=timeout
        )
        shared = {
            "token": token or os.environ.get("UKC_TOKEN"),
            "headers": headers,
            "user_agent": user_agent or USER_AGENT,
            "http": self._http,
        }
        platform = ApiClientConfig(base_url=resolved, **shared)  # type: ignore[arg-type]
        control_plane = ApiClientConfig(
            base_url=control_plane_url or CONTROLPLANE_BASE_URL,
            **shared,  # type: ignore[arg-type]
        )

        session = Session(
            SessionConfig(
                platform=platform,
                control_plane=control_plane,
                default_metro=default_metro,
                pinned=(MetroEndpoint(metro=resolved, base_url=resolved) if explicit_url else None),
            )
        )
        super().__init__(session, _default_scope(metros, chosen_metro))

        #: The raw ("plumbing") API surfaces: ``api.platform`` (metro-scoped,
        #: pointing at the default metro unless a call passes ``base_url``) and
        #: ``api.controlplane``.
        self.api = Api(platform, control_plane)
        self._metro_clients: dict[str, MetroClient] = {}

    async def aclose(self) -> None:
        """Release the connection pool, unless an httpx client was supplied."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    def metro(self, metro: Metro) -> MetroClient:
        """The resource clients for a single metro.

        Cached, so repeated calls share one set of clients.

        .. code-block:: python

            fra = ukc.metro("fra")
            await fra.instances.create(image="nginx:latest")
        """
        endpoint = self._session.pinned or MetroEndpoint(
            metro=metro, base_url=metro_base_url(metro)
        )
        cached = self._metro_clients.get(endpoint.base_url)
        if cached is not None:
            return cached
        client = MetroClient(self._session, endpoint)
        self._metro_clients[endpoint.base_url] = client
        return client

    def metros(self, scope: MetroScope) -> Scope:
        """The resource clients for several metros, or for every metro (``"all"``).

        .. code-block:: python

            async for inst in ukc.metros(["fra", "dal"]).instances.list():
                ...
        """
        return Scope(self._session, scope)

    async def available_metros(self) -> list[MetroEndpoint]:
        """Every metro this account can reach, as reported by the control plane.

        Cached for the client's lifetime.
        """
        return await self._session.discover()


def _default_scope(metros: MetroScope | None, metro: Metro | None) -> MetroScope:
    """Work out the default scope: an explicit list, a pinned metro, or every metro."""
    if metros is not None:
        return metros
    return metro or "all"
