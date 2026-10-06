# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Where a plugin is reached. Kept apart from the package's __init__ so the
# per-plugin packages can import it without a cycle.

from __future__ import annotations

import re
from urllib.parse import quote

from ...core.http import normalise_base_url

__all__ = ["plugin_base_url", "plugin_origin"]

#: The instance route a plugin is proxied under, at the end of a base URL.
_ROUTE = re.compile(r"/v1/instances/[^/]+/plugins/[^/]+$")


def plugin_base_url(base_url: str, instance_uuid: str, plugin: str) -> str:
    """The plugin route of one instance, to use as a client's ``base_url``.

    A plugin runs inside an instance, and the platform proxies its API under the
    instance on the metro that runs it::

        https://api.<metro>.unikraft.cloud/v1/instances/<uuid>/plugins/<name>/<path>

    ``base_url`` is that metro's API base URL, e.g. ``https://api.fra.unikraft.cloud``,
    with or without the ``/v1`` the control plane reports it with. The UUID and
    the plugin name are one path segment each, so each is percent-encoded with
    nothing left unescaped.
    """
    return (
        f"{normalise_base_url(base_url)}/v1/instances/{quote(instance_uuid, safe='')}"
        f"/plugins/{quote(plugin, safe='')}"
    )


def plugin_origin(base_url: str) -> str:
    """The metro API base URL a plugin route was built from.

    A base URL that is no plugin route is its own origin, normalised, so a
    client made at a route and one made at a metro build routes alike.
    """
    return _ROUTE.sub("", normalise_base_url(base_url))
