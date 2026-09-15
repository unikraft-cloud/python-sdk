# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Plugins: helper programs loaded into an instance beside its workload, each
# reached over the instance's authenticated plugin route on the metro that runs
# it. This is the generic part -- addressing one -- that every typed plugin
# client (the sandbox, for one) is built on.

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from ..api.plugins import plugin_base_url
from ..core.handle import MetroTarget, spent
from ..core.http import ApiClientConfig
from ..core.metro import Metro

if TYPE_CHECKING:
    from ..resources.instances import Instance

__all__ = ["Plugin", "PluginRoute", "ResolvedInstance"]

C = TypeVar("C")


@dataclass(frozen=True)
class PluginRoute:
    """Where a plugin on one instance is reached.

    The platform proxies a plugin's API under the instance that runs it, on the
    metro holding that instance::

        https://api.<metro>.unikraft.cloud/v1/instances/<uuid>/plugins/<name>/

    The proxy resolves the instance by UUID, which is why the route carries one.
    """

    #: The metro holding the instance.
    metro: Metro
    #: That metro's API base URL.
    base_url: str
    #: The instance the plugin runs in.
    instance_uuid: str
    #: The name the plugin was attached under.
    name: str

    @property
    def url(self) -> str:
        """The route itself, to use as a client's ``base_url``."""
        return plugin_base_url(self.base_url, self.instance_uuid, self.name)


@dataclass(frozen=True)
class ResolvedInstance:
    """What a handle knows about its instance once it has been located.

    Whatever is already in hand travels along so it need not be fetched again: a
    UUID reference carries the UUID, and a handle that located, created or
    waited for the instance carries what that returned. A name pinned to one
    metro carries neither, and costs one read.
    """

    #: The instance's reference and the metro holding it.
    target: MetroTarget
    #: The UUID, when it is known without a request.
    uuid: str | None = None
    #: The instance, when the handle already has it.
    instance: Instance | None = None


class Plugin:
    """A plugin on one instance, addressed lazily.

    Obtained from an instance handle. Nothing is sent until the route is needed,
    and resolving it reads the instance only when its UUID is not yet known.

    .. code-block:: python

        plugin = ukc.instances.get(name="web").plugin("sandbox")
        route = await plugin.route()
        raw = await plugin.client(SandboxApi)
    """

    def __init__(
        self,
        name: str,
        *,
        resolve: Callable[[], Awaitable[ResolvedInstance]],
        read: Callable[[MetroTarget], Awaitable[Instance]],
        config: ApiClientConfig,
    ) -> None:
        #: The name the plugin was attached under.
        self.name = name
        self._resolve = resolve
        self._read = read
        self._config = config
        self._route: asyncio.Future[PluginRoute] | None = None
        self._reading: asyncio.Future[Instance] | None = None
        self._target: MetroTarget | None = None
        self._instance: Instance | None = None

    async def route(self) -> PluginRoute:
        """Where the plugin is reached, resolving the instance once.

        Concurrent callers share one lookup, and one a caller gave up on runs
        on and serves the next call. A lookup that failed is not kept: the
        next call looks the instance up again.
        """
        if spent(self._route):
            # Memoised as a task rather than a coroutine so that concurrent
            # callers -- a wait_ready() racing a run() -- share the one lookup.
            self._route = asyncio.ensure_future(self._locate())
        # Shielded: the task is shared, so one caller giving up on it must not
        # cancel the lookup every other caller is waiting on.
        assert self._route is not None
        return await asyncio.shield(self._route)

    async def _locate(self) -> PluginRoute:
        resolved = await self._resolve()
        self._target = resolved.target
        self._instance = resolved.instance
        uuid = resolved.uuid
        if uuid is None:
            self._instance = await self._read(resolved.target)
            uuid = self._instance.uuid
            # The route is built from the UUID, so a read that reports none
            # leaves the plugin unaddressable.
            if uuid is None:  # pragma: no cover - the platform always reports one
                raise RuntimeError(f"the instance reported no UUID to address {self.name} by")
        return PluginRoute(
            metro=resolved.target.metro,
            base_url=resolved.target.base_url,
            instance_uuid=uuid,
            name=self.name,
        )

    async def instance(self) -> Instance:
        """The instance the plugin runs in, read once.

        Concurrent callers share the one read, and one the caller waiting on it
        gave up on runs on and serves the next call. A read that failed is made
        again on the next call.
        """
        await self.route()
        if self._instance is not None:
            return self._instance
        if spent(self._reading):
            self._reading = asyncio.ensure_future(self._read_instance())
        assert self._reading is not None
        return await asyncio.shield(self._reading)

    async def _read_instance(self) -> Instance:
        target = self._target
        if target is None:  # pragma: no cover - _locate sets it before route() returns
            raise RuntimeError("plugin route resolved without a target")
        self._instance = await self._read(target)
        return self._instance

    async def client(self, factory: Callable[[ApiClientConfig], C]) -> C:
        """Build a client of any kind pointed at the plugin's route.

        ``factory`` receives the platform transport configuration -- token,
        headers, connection pool -- re-pointed at the route, so a generated
        plumbing client such as ``SandboxApi`` works as it is.
        """
        route = await self.route()
        return factory(self._config.with_base_url(route.url))
