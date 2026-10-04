# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The sandbox plugin API's "plumbing" layer. The generated clients come from
# the unikraft-cloud-plugin-sandbox-api package, which plugin-sdk renders from
# the plugin's specification; what is here points them at an instance and
# sends their requests through the SDK's transport.

from __future__ import annotations

from dataclasses import replace
from types import TracebackType

from typing_extensions import Self
from unikraft_cloud_plugin_sandbox_api import (
    PLUGIN_NAME,
    CommandsApi,
    FsApi,
    SandboxPluginApi,
    models,
)

from ....core.http import ApiClient, ApiClientConfig, RawResponse
from .._route import plugin_base_url, plugin_origin

__all__ = [
    "PLUGIN_NAME",
    "ApiClient",
    "ApiClientConfig",
    "CommandsApi",
    "FsApi",
    "RawResponse",
    "SandboxApi",
    "SandboxPluginApi",
    "models",
]


class SandboxApi(SandboxPluginApi):
    """Every sandbox plugin API resource, raw, sent through the SDK's transport.

    The plugin API is instance-scoped: the platform proxies it under
    ``/v1/instances/<uuid>/plugins/<name>/`` on the metro that runs the
    instance. :meth:`for_instance` returns this client pointed at one instance's
    route; alternatively a single call can be redirected with ``base_url=``.

    A client built on its own owns a connection pool, which every client
    scoped from it shares; close the one that made it, as below, or await its
    :meth:`aclose`. Reached as ``ukc.api.plugins.sandbox`` it sends through the
    session's pool instead, and the session's close releases that.

    .. code-block:: python

        from unikraft_cloud.api.plugins.sandbox import SandboxApi
        from unikraft_cloud.core.http import ApiClientConfig

        config = ApiClientConfig(
            base_url="https://api.fra.unikraft.cloud", token=os.environ["UKC_TOKEN"]
        )
        async with SandboxApi(config) as sandbox:
            api = sandbox.for_instance("550e8400-e29b-41d4-a716-446655440000")
            res = await api.commands.list_commands()
    """

    def __init__(self, config: ApiClientConfig) -> None:
        self._config = config
        #: The metro API base URL that instance routes are built from, also for a
        #: client made at an instance's route.
        self._origin = plugin_origin(config.base_url)
        #: The SDK client that every resource sends through, so they share a pool.
        self.client = ApiClient(config)
        super().__init__(self.client)

    async def aclose(self) -> None:
        """Release the connection pool, if this client is the one that made it."""
        await self.client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    def for_instance(
        self,
        uuid: str,
        *,
        plugin: str = PLUGIN_NAME,
        base_url: str | None = None,
    ) -> SandboxApi:
        """This client pointed at the plugin route of one instance.

        ``base_url`` is the API base URL of the metro running the instance, when
        it is not the one this client was configured with, or routed from.
        ``plugin`` is the name the plugin was attached under, when it is not the
        default. The scoped client sends through this one's pool, so closing
        this one closes it too.
        """
        route = plugin_base_url(base_url or self._origin, uuid, plugin)
        config = replace(self._config.with_base_url(route), http=self.client.http)
        return SandboxApi(config)
