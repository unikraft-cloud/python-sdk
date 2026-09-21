# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The raw ("plumbing") layer of both Unikraft Cloud APIs, in one place.
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

__all__ = ["Api", "ControlPlaneApi", "PlatformApi"]


class Api(ApiClientGroup):
    """Both raw API surfaces behind one set of credentials, as exposed by ``ukc.api``.

    Both share one connection pool, and closing this releases it -- unless an
    httpx client was supplied, whose lifetime stays its owner's.

    .. code-block:: python

        await ukc.api.platform.instances.get_instances(count=10)
        await ukc.api.controlplane.metros.list_metros()
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

    async def aclose(self) -> None:
        """Release the pool, and the control plane's own if it made one."""
        await self.controlplane.aclose()
        await super().aclose()
