# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The platform API's "plumbing" layer: the generated clients, plus a container
# that groups them behind one transport config. Everything here returns the
# response envelope exactly as the OpenAPI specification describes it.

from __future__ import annotations

from ...core.http import ApiClient, ApiClientConfig
from . import models_gen as models
from .autoscale_gen import AutoscaleApi
from .certificates_gen import CertificatesApi
from .images_gen import ImagesApi
from .instances_gen import InstancesApi
from .node_gen import NodeApi
from .service_groups_gen import ServiceGroupsApi
from .users_gen import UsersApi
from .volumes_gen import VolumesApi

__all__ = [
    "ApiClient",
    "ApiClientConfig",
    "AutoscaleApi",
    "CertificatesApi",
    "ImagesApi",
    "InstancesApi",
    "NodeApi",
    "PlatformApi",
    "ServiceGroupsApi",
    "UsersApi",
    "VolumesApi",
    "models",
]


class PlatformApi:
    """Every platform API resource, raw.

    The platform API is metro-scoped: these clients talk to the one metro their
    ``base_url`` names, and a single call can be redirected with ``base_url=``.
    Fanning out across metros is the idiomatic layer's job.

    .. code-block:: python

        from unikraft_cloud.api.platform import PlatformApi
        from unikraft_cloud.core.http import ApiClientConfig

        api = PlatformApi(
            ApiClientConfig(
                base_url="https://api.fra.unikraft.cloud",
                token=os.environ["UKC_TOKEN"],
            )
        )
        res = await api.instances.get_instances(count=10)
    """

    def __init__(self, config: ApiClientConfig) -> None:
        self.autoscale = AutoscaleApi(config)
        self.certificates = CertificatesApi(config)
        self.images = ImagesApi(config)
        self.instances = InstancesApi(config)
        self.node = NodeApi(config)
        self.services = ServiceGroupsApi(config)
        self.users = UsersApi(config)
        self.volumes = VolumesApi(config)
