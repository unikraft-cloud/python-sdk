# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The raw ("plumbing") layer of both Unikraft Cloud APIs, in one place.
# Everything here mirrors the OpenAPI specification: operations are named after
# their operation ID, and responses come back as the untouched envelope.
#
# The idiomatic ("porcelain") layer lives at the package root and is built on
# top of this.

from __future__ import annotations

from ..core.http import ApiClientConfig
from .controlplane import ControlPlaneApi
from .platform import PlatformApi

__all__ = ["Api", "ControlPlaneApi", "PlatformApi"]


class Api:
    """Both raw API surfaces behind one set of credentials, as exposed by ``ukc.api``.

    .. code-block:: python

        await ukc.api.platform.instances.get_instances(count=10)
        await ukc.api.controlplane.metros.list_metros()
    """

    def __init__(self, platform: ApiClientConfig, control_plane: ApiClientConfig) -> None:
        #: The metro-scoped platform API.
        self.platform = PlatformApi(platform)
        #: The global control-plane API.
        self.controlplane = ControlPlaneApi(control_plane)
