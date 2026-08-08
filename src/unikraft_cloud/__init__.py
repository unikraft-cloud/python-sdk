# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

"""Official Python SDK for the Unikraft Cloud Platform API.

The idiomatic client is :class:`UnikraftCloud`. The raw, spec-shaped API stays
available on ``ukc.api`` and from ``unikraft_cloud.api.platform`` and
``unikraft_cloud.api.controlplane``.
"""

from __future__ import annotations

from .api import Api, ControlPlaneApi, PlatformApi
from .client import USER_AGENT, MetroClient, Scope, UnikraftCloud
from .core.errors import (
    AuthenticationError,
    ErrorKind,
    NotFoundError,
    RateLimitError,
    ResponseError,
    ServerError,
    UnikraftCloudError,
)
from .core.fanout import (
    AmbiguousRefError,
    MetroFailure,
    MetroFanoutError,
    MetroFulfilled,
    MetroOutcome,
    MetroRejected,
)
from .core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from .core.handle_set import HandleSet
from .core.http import (
    UNSET,
    ApiClient,
    ApiClientConfig,
    CallOptions,
    TimeoutOption,
    Unset,
)
from .core.metro import (
    CONTROLPLANE_BASE_URL,
    DEFAULT_METRO,
    KNOWN_METROS,
    Metro,
    MetroEndpoint,
    MetroScope,
    metro_base_url,
    metro_endpoint,
    with_metro,
)
from .core.pagination import collect, paginate
from .core.patch import REMOVE, PatchItem, PatchOp, Remove, ResourceEditor
from .core.resource import MetroGroup, Resource, ScopeOptions
from .core.response import Ref, RefLike, or_absent
from .core.session import Session, SessionConfig
from .resources.instances import (
    DeletedInstance,
    Instance,
    InstanceEditor,
    InstanceHandle,
    InstanceHistory,
    InstanceLogs,
    InstanceMetrics,
    Instances,
    InstanceSet,
    StartedInstance,
    StoppedInstance,
    SuspendedInstance,
    UpdatedInstance,
    WaitedInstance,
)

__version__ = "0.1.0"

__all__ = [
    "CONTROLPLANE_BASE_URL",
    "DEFAULT_METRO",
    "KNOWN_METROS",
    "REMOVE",
    "UNSET",
    "USER_AGENT",
    "AmbiguousRefError",
    "Api",
    "ApiClient",
    "ApiClientConfig",
    "AuthenticationError",
    "CallOptions",
    "ControlPlaneApi",
    "DeletedInstance",
    "ErrorKind",
    "HandleSet",
    "HandleSteps",
    "Instance",
    "InstanceEditor",
    "InstanceHandle",
    "InstanceHistory",
    "InstanceLogs",
    "InstanceMetrics",
    "InstanceSet",
    "Instances",
    "Located",
    "Metro",
    "MetroClient",
    "MetroEndpoint",
    "MetroFailure",
    "MetroFanoutError",
    "MetroFulfilled",
    "MetroGroup",
    "MetroOutcome",
    "MetroRejected",
    "MetroScope",
    "MetroTarget",
    "NotFoundError",
    "PatchItem",
    "PatchOp",
    "PlatformApi",
    "RateLimitError",
    "Ref",
    "RefLike",
    "Remove",
    "Resource",
    "ResourceEditor",
    "ResourceHandle",
    "ResponseError",
    "Scope",
    "ScopeOptions",
    "ServerError",
    "Session",
    "SessionConfig",
    "StartedInstance",
    "StoppedInstance",
    "SuspendedInstance",
    "TimeoutOption",
    "UnikraftCloud",
    "UnikraftCloudError",
    "Unset",
    "UpdatedInstance",
    "WaitedInstance",
    "__version__",
    "collect",
    "metro_base_url",
    "metro_endpoint",
    "or_absent",
    "paginate",
    "with_metro",
]
