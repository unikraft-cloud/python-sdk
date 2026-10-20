# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The build API's "plumbing" layer: the generated client, plus a container
# that holds it behind one transport config. Everything here returns the
# response exactly as the OpenAPI specification describes it; the build API
# has no envelope. The progress stream of a build is not generated: it is
# `Builds.logs` and `Builds.plain_logs` in the idiomatic layer.

from __future__ import annotations

from ...core.http import ApiClient, ApiClientConfig, ApiClientGroup
from . import models_gen as models
from .builds_gen import BuildsApi

__all__ = ["ApiClient", "ApiClientConfig", "BuildApi", "BuildsApi", "models"]


class BuildApi(ApiClientGroup):
    """The build API, raw.

    Unless ``config.http`` supplied the connection pool, the container owns it
    and releases it on ``async with`` exit or :meth:`aclose`.

    .. code-block:: python

        from unikraft_cloud.api.build import BuildApi

        async with BuildApi(config) as api:
            res = await api.builds.list_builds()
    """

    def __init__(self, config: ApiClientConfig) -> None:
        super().__init__(config)
        self.builds = BuildsApi(self.config)
