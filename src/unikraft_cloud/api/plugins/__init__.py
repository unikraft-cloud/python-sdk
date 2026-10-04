# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The raw ("plumbing") layer of the official plugin APIs. A plugin runs inside
# an instance and is reached through the instance's authenticated plugin route,
# so every plugin client is pointed at one instance before it is used.

from __future__ import annotations

from ...core.http import ApiClientConfig, ApiClientGroup
from ._route import plugin_base_url
from .sandbox import SandboxApi

__all__ = ["PluginsApi", "SandboxApi", "plugin_base_url"]


class PluginsApi(ApiClientGroup):
    """The raw clients of the official plugins, as exposed by ``ukc.api.plugins``.

    Each is built on the platform API's transport config and points at that
    config's metro until :meth:`~SandboxApi.for_instance` names an instance.
    Built on its own, the group owns the connection pool its members share,
    and :meth:`aclose` or ``async with`` releases it, as for the other API
    groups.

    .. code-block:: python

        raw = ukc.metro("fra").api.plugins.sandbox.for_instance(instance.uuid)
        res = await raw.commands.list_commands()
    """

    def __init__(self, config: ApiClientConfig) -> None:
        super().__init__(config)
        #: The sandbox plugin: commands and files inside an instance.
        self.sandbox = SandboxApi(self.config)
