# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Instance templates: prepare one, clone instances out of it, and look an
# image up in the registry first. Run with:
#   UKC_TOKEN=... uv run examples/templates.py <namespace>/<image>:<tag>

from __future__ import annotations

import asyncio
import sys

from unikraft_cloud import UnikraftCloud, UnikraftCloudError


async def main(image: str) -> None:
    async with UnikraftCloud() as ukc:  # token from UKC_TOKEN
        fra = ukc.metro("fra")

        # The registry, not a node's cache, says whether the image can be pulled.
        found = await ukc.images.find(image)
        if found is None:
            raise SystemExit(f"{image} is not in the registry")
        print(f"{found.reference} is {found.size} bytes, digest {found.digest}")

        # The guest decides when it is snapshotted by writing to the template
        # control file; this one does so at once. A template that already exists
        # is read and returned, so this is safe to call every time.
        template = await fra.templates.prepare(
            "sdk-example",
            create_args={
                "image": image,
                "memory_mb": 512,
                "args": ["/bin/sh", "-c", "echo 1 > /uk/libukp/template_instance; sleep infinity"],
                "tags": ["sdk-example"],
            },
            prepare_timeout_seconds=120,
        )
        print(f"template {template.name} ({template.uuid}) is {template.state}")

        # A clone takes what an instance create takes, apart from the image and
        # the template.
        clone = await fra.templates.get(name="sdk-example").clone(
            tags=["sdk-example"], autostart=True, timeout_s=60
        )
        print(f"clone {clone.name} is {clone.state}")

        # Tags address everything the example made, so the cleanup is one call
        # per resource type and can run again.
        await fra.instances.each(tags=["sdk-example"]).delete(missing_ok=True)
        await fra.templates.each(tags=["sdk-example"]).delete(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <namespace>/<image>:<tag>", file=sys.stderr)
        raise SystemExit(2)
    try:
        asyncio.run(main(sys.argv[1]))
    except UnikraftCloudError as err:
        print(f"API error ({err.status or '?'}): {err}", file=sys.stderr)
        raise SystemExit(1) from err
