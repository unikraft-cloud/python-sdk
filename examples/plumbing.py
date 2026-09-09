# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Using the low-level "plumbing" API directly. Every method returns the raw
# response envelope exactly as described by the OpenAPI specification, and each
# client talks to exactly one metro. Reach for this when you need a field or an
# operation the idiomatic layer does not expose yet.
#
#   UKC_TOKEN=... uv run examples/plumbing.py

from __future__ import annotations

import asyncio
import os

import httpx

from unikraft_cloud import ApiClientConfig
from unikraft_cloud.api.controlplane import ControlPlaneApi
from unikraft_cloud.api.platform import InstancesApi, PlatformApi


async def main() -> None:
    token = os.environ.get("UKC_TOKEN")

    # One httpx client shared by every plumbing client below, so they pool their
    # connections together and there is a single thing to close.
    async with httpx.AsyncClient() as http:
        platform_config = ApiClientConfig(
            base_url="https://api.fra.unikraft.cloud", token=token, http=http
        )

        # One resource at a time...
        instances = InstancesApi(platform_config)

        # ...or every platform resource behind one config.
        platform = PlatformApi(platform_config)

        # The control plane is global rather than metro-scoped.
        controlplane = ControlPlaneApi(
            ApiClientConfig(base_url="https://controlplane.unikraft.cloud", token=token, http=http)
        )

        res = await instances.get_instances(count=10, details=True)
        print(f"status: {res.status}, op_time_us: {res.op_time_us}")
        for inst in res.data.instances if res.data and res.data.instances else []:
            print(f"- {inst.name}")

        quotas = await platform.users.get_user()
        print(quotas.data.quotas if quotas.data else [])

        # Ask the control plane where the metros are, then aim a single call at
        # one of them with a per-call `base_url` -- this is the fan-out the
        # idiomatic layer does for you.
        listed = await controlplane.metros.list_metros()
        for found in listed.data.metros if listed.data and listed.data.metros else []:
            there = await instances.get_instances(count=1, base_url=found.endpoint)
            how_many = len(there.data.instances or []) if there.data else 0
            print(f"{found.iata_code}: {how_many} instance(s)")


if __name__ == "__main__":
    asyncio.run(main())
