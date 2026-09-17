# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The control plane's "plumbing" layer. Unlike the platform API the control plane
# is global rather than metro-scoped, so there is one endpoint to talk to.

from __future__ import annotations

from ...core.http import ApiClient, ApiClientConfig, ApiClientGroup
from . import models_gen as models
from .auth_gen import AuthApi
from .images_gen import ImagesApi
from .metros_gen import MetrosApi
from .node_activation_service_gen import NodeActivationServiceApi
from .node_service_gen import NodeServiceApi

__all__ = [
    "ApiClient",
    "ApiClientConfig",
    "AuthApi",
    "ControlPlaneApi",
    "ImagesApi",
    "MetrosApi",
    "NodeActivationServiceApi",
    "NodeServiceApi",
    "models",
]


class ControlPlaneApi(ApiClientGroup):
    """Every control-plane resource, raw.

    The resources share one connection pool. Unless ``config.http`` supplied
    it, the container owns that pool and releases it on ``async with`` exit or
    :meth:`aclose`.

    .. code-block:: python

        from unikraft_cloud.api.controlplane import ControlPlaneApi

        async with ControlPlaneApi(config) as api:
            res = await api.metros.list_metros()
    """

    def __init__(self, config: ApiClientConfig) -> None:
        super().__init__(config)
        self.auth = AuthApi(self.config)
        self.images = ImagesApi(self.config)
        self.metros = MetrosApi(self.config)
        self.node_activation = NodeActivationServiceApi(self.config)
        self.nodes = NodeServiceApi(self.config)
