# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The control plane's "plumbing" layer. Unlike the platform API the control plane
# is global rather than metro-scoped, so there is one endpoint to talk to.

from __future__ import annotations

from ...core.http import ApiClient, ApiClientConfig
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


class ControlPlaneApi:
    """Every control-plane resource, raw.

    .. code-block:: python

        from unikraft_cloud.api.controlplane import ControlPlaneApi

        api = ControlPlaneApi(config)
        res = await api.metros.list_metros()
    """

    def __init__(self, config: ApiClientConfig) -> None:
        self.auth = AuthApi(config)
        self.images = ImagesApi(config)
        self.metros = MetrosApi(config)
        self.node_activation = NodeActivationServiceApi(config)
        self.nodes = NodeServiceApi(config)
