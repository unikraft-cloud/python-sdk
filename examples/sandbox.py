# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The sandbox plugin: run commands and move files inside an instance. Run with:
#   UKC_TOKEN=... uv run examples/sandbox.py <namespace>/<image>:<tag>

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from unikraft_cloud import ExecTimeoutError, OutputChunk, UnikraftCloud, UnikraftCloudError


def show(chunk: OutputChunk) -> None:
    """Print a piece of output as it arrives, on the stream it came from."""
    out = sys.stderr if chunk.stream == "stderr" else sys.stdout
    out.write(chunk.data.decode(errors="replace"))
    out.flush()


async def main(image: str) -> None:
    async with UnikraftCloud() as ukc:  # token from UKC_TOKEN
        fra = ukc.metro("fra")

        # The plugin is attached at creation. The instance only has to stay up:
        # the plugin runs the commands.
        instance = await fra.instances.create(
            image=image,
            memory_mb=1024,
            args=["/bin/sh", "-c", "sleep infinity"],
            plugins=[{"name": "sandbox", "image": "plugins/sandbox:latest", "config": {}}],
            autostart=True,
            timeout_s=60,
        )
        handle = fra.instances.get(uuid=instance.uuid)
        try:
            sb = handle.sandbox()
            await sb.wait_ready(timeout=60)

            # A shell line, with its output printed as it arrives and collected.
            result = await sb.exec("echo hello; uname -a", on_output=show, forget=True)
            print(f"exit code {result.exit_code}")

            # An argument vector runs without a shell: nothing to quote.
            result = await sb.exec(["printf", "%s\n", "a b c"])
            print(result.stdout.decode(), end="")

            # A timeout interrupts the command; a grace period bounds the wait
            # for one that ignores the interrupt.
            try:
                result = await sb.exec("sleep 300", timeout=2, wait_delay=5)
                print(f"interrupted: exit code {result.exit_code}")
            except ExecTimeoutError as err:
                await err.command.signal("KILL")
                print(f"gave up on {err.command.uuid}")

            # Files move in chunks, so no request size limit applies.
            await sb.fs.write("/tmp/hello.txt", "hello from the SDK\n", parents=True)
            print(await sb.fs.read_text("/tmp/hello.txt"), end="")
            with tempfile.TemporaryDirectory() as tmp:
                local = Path(tmp) / "hello.txt"
                size = await sb.fs.read_to("/tmp/hello.txt", local)
                print(f"downloaded {size} bytes to {local.name}")
        finally:
            await handle.delete(timeout_seconds=60, missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <namespace>/<image>:<tag>", file=sys.stderr)
        raise SystemExit(2)
    try:
        asyncio.run(main(sys.argv[1]))
    except UnikraftCloudError as err:
        print(f"API error ({err.status or '?'}): {err}", file=sys.stderr)
        raise SystemExit(1) from err
