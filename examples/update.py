# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Changing an instance's properties. Run with:
#   UKC_TOKEN=... uv run examples/update.py

from __future__ import annotations

import asyncio
import sys

from unikraft_cloud import REMOVE, PatchItem, UnikraftCloud, UnikraftCloudError


async def main() -> None:
    async with UnikraftCloud() as ukc:
        fra = ukc.metro("fra")

        # Properties are keyword arguments: a value sets the property, REMOVE
        # clears it, and anything omitted is left alone. One request, whatever
        # you pass.
        updated = await fra.instances.get(name="web").update(
            memory_mb=512,
            vcpus=2,
            env={"LOG_LEVEL": "debug"},
            autokill=REMOVE,
        )
        print(f"{updated.name} in {updated.metro}: {updated.status}")

        # When `set` is not what you mean -- merge into a property, or remove
        # single members -- stage the operations and apply them together.
        await (
            fra.instances.get(name="web")
            .edit()
            .set(hostname="web-1")
            .add(env={"FEATURE_X": "1"}, tags=["prod"])
            .delete(env=["LOG_LEVEL"], tags=["staging"])
            .apply()
        )

        # `apply()` returns a handle, so the chain continues.
        await fra.instances.get(name="web").edit().set(memory_mb=1024).apply().wait(state="running")

        # The raw triples remain available for anything keyword arguments cannot
        # express.
        await fra.instances.get(name="web").patch([PatchItem("memory_mb", "set", 256)])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except UnikraftCloudError as err:
        print(f"API error ({err.status or '?'}): {err}", file=sys.stderr)
        raise SystemExit(1) from err
