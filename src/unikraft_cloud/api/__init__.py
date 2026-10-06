# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The raw ("plumbing") layer of every Unikraft Cloud API, in one place.
# Everything here mirrors the OpenAPI specification: operations are named after
# their operation ID, and responses come back as the untouched envelope.
#
# The idiomatic ("porcelain") layer lives at the package root and is built on
# top of this.

from __future__ import annotations

from dataclasses import replace

from ..core.http import ApiClientConfig, ApiClientGroup
from .controlplane import ControlPlaneApi
from .platform import PlatformApi
from .plugins import PluginsApi
from .plugins.sandbox import SandboxApi

__all__ = ["Api", "ControlPlaneApi", "PlatformApi", "PluginsApi", "SandboxApi"]


class Api(ApiClientGroup):
    """Every raw API surface behind one set of credentials, as exposed by ``ukc.api``.

    They share one connection pool, and closing this releases it -- unless an
    httpx client was supplied, whose lifetime stays its owner's.

    .. code-block:: python

        await ukc.api.platform.instances.get_instances(count=10)
        await ukc.api.controlplane.metros.list_metros()
        await ukc.api.plugins.sandbox.for_instance(uuid).commands.list_commands()
    """

    def __init__(self, platform: ApiClientConfig, control_plane: ApiClientConfig) -> None:
        super().__init__(platform)
        #: The metro-scoped platform API.
        self.platform = PlatformApi(self.config)
        # The control plane shares the pool unless it was configured to connect
        # differently, which is its to honour rather than to override.
        shared = (control_plane.http, control_plane.transport, control_plane.trust_env) == (
            platform.http,
            platform.transport,
            platform.trust_env,
        )
        #: The global control-plane API.
        self.controlplane = ControlPlaneApi(
            replace(control_plane, http=self.http) if shared else control_plane
        )
        #: The official plugin APIs, reached through an instance on the platform
        #: API's metro.
        self.plugins = PluginsApi(self.config)

    async def aclose(self) -> None:
        """Release the pool, and the control plane's own if it made one."""
        await self.controlplane.aclose()
        await super().aclose()
