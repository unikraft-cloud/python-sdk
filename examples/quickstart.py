# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Idiomatic quickstart. Run with:
#   UKC_TOKEN=... uv run examples/quickstart.py

from __future__ import annotations

import asyncio
import base64
import sys

from unikraft_cloud import UnikraftCloud, UnikraftCloudError


async def main() -> None:
    async with UnikraftCloud() as ukc:  # token from UKC_TOKEN
        # Creating a resource happens in one metro. Name it, and every operation
        # on that client needs no lookup.
        fra = ukc.metro("fra")

        instance = await fra.instances.create(
            image="nginx:latest",
            memory_mb=256,
            autostart=True,
            service_group={
                "services": [
                    {"port": 443, "handlers": ["tls", "http"], "destination_port": 80},
                ],
            },
        )
        print(f"created {instance.name} ({instance.uuid}) in {instance.metro}")

        # Operations chain off a reference: this waits for the instance to come
        # up, then reads the tail of its console log.
        logs = await (
            fra.instances.get(uuid=instance.uuid)
            .wait(state="running", timeout_seconds=30)
            .logs(offset=-4096)
        )
        print(base64.b64decode(logs.output or "").decode(errors="replace"))

        # Without a metro, the client is account-wide: every metro is asked in
        # parallel and the pages are merged as they arrive.
        async for found in ukc.instances.list(details=True):
            print(f"- {found.metro}/{found.name}: {found.state}")

        # A handle resolves to the metro that actually holds the instance, so the
        # suspend is sent there and nowhere else.
        await ukc.instances.get(name=instance.name).suspend()

        # Bulk operations take one reference or a list of them.
        await fra.instances.delete([{"uuid": instance.uuid}])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except UnikraftCloudError as err:
        print(f"API error ({err.status or '?'}): {err}", file=sys.stderr)
        raise SystemExit(1) from err
