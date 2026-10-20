# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Several builds on the remote build service at once, followed side by side.
# Each argument after the image namespace is a directory of
# github.com/unikraft-cloud/examples, pushed to <namespace>/<directory>:latest:
#   UKC_TOKEN=... uv run examples/parallel.py index.unikraft.io/<user> nginx redis
#
# Progress goes to stderr with each line prefixed by its directory, and the
# pushed ref@digest of every build to stdout.

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys

from unikraft_cloud import (
    UnikraftCloud,
    UnikraftCloudError,
    git_source,
    image_output,
    kraftfile_from,
)

# The ANSI colours of the prefixes, in docker compose's order.
COLOURS = ["36", "33", "32", "35", "34", "36;1", "33;1", "32;1", "35;1", "34;1"]


async def main(args: argparse.Namespace) -> None:
    dirs = args.dirs or ["mariadb", "neo4j", "visual-studio-code-server"]
    colour = sys.stderr.isatty()
    width = max(len(d) for d in dirs)
    async with UnikraftCloud(build_url=args.server) as ukc:  # token from UKC_TOKEN
        builds = []
        for index, subdir in enumerate(dirs):
            prefix = f"{subdir:<{width}} | "
            if colour:
                prefix = f"\x1b[{COLOURS[index % len(COLOURS)]}m{prefix}\x1b[0m"
            builds.append(run(ukc, args, subdir, prefix))
        # Every build runs to its end; the failures are reported together.
        failures = [
            f"{subdir}: {outcome}"
            for subdir, outcome in zip(
                dirs, await asyncio.gather(*builds, return_exceptions=True), strict=True
            )
            if outcome is not None
        ]
    if failures:
        print("parallel: " + "; ".join(failures), file=sys.stderr)
        raise SystemExit(1)


async def run(ukc: UnikraftCloud, args: argparse.Namespace, subdir: str, prefix: str) -> str | None:
    """Run one build to its end, printing its progress behind `prefix`; None once it pushed."""
    src = git_source(args.git, args.ref or None, subdir=subdir)
    build = await ukc.builds.create(
        kraftfile=kraftfile_from(src),
        contexts={"context": src},
        output=[image_output(f"{args.namespace}/{subdir}:latest")],
    )
    print(f"{prefix}build {build.id}", file=sys.stderr)

    try:
        while True:
            async with contextlib.aclosing(build.plain_logs()) as lines:
                tail = ""
                async for text in lines:
                    *whole, tail = (tail + text).split("\n")
                    for line in whole:
                        print(f"{prefix}{line}", file=sys.stderr)
                if tail:
                    print(f"{prefix}{tail}", file=sys.stderr)
            build = await build.refresh()
            if build.status not in ("waiting", "running"):
                break
    except asyncio.CancelledError:
        await build.cancel()
        raise

    if build.result is None:
        return f"build {build.id} {build.status}: {build.error}"
    for img in build.result.images or []:
        print(f"{img.ref}@{img.digest}")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build directories of a git repository at once on the remote build service "
        "and push each to <namespace>/<directory>:latest."
    )
    parser.add_argument("namespace", help="where to push, e.g. index.unikraft.io/<user>")
    parser.add_argument("dirs", nargs="*", help="directories of the repository to build")
    parser.add_argument("--server", default=None, help="build service URL, or $UKC_BUILD_SERVER")
    parser.add_argument(
        "--git",
        default="https://github.com/unikraft-cloud/examples.git",
        help="git repository to build",
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="branch, tag or commit to build, or empty for the default branch",
    )
    try:
        asyncio.run(main(parser.parse_args()))
    except KeyboardInterrupt:
        sys.exit(130)
    except UnikraftCloudError as err:
        print(f"API error ({err.status or '?'}): {err}", file=sys.stderr)
        raise SystemExit(1) from err
