# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# A detached build on the remote build service: the source, the Kraftfile and
# the output all go in the request, and the build runs entirely server side.
# Every input but the token and the image to push has a default, which builds
# the nginx example of github.com/unikraft-cloud/examples:
#   UKC_TOKEN=... uv run examples/detached.py index.unikraft.io/<user>/nginx:latest
#
# Progress goes to stderr and the pushed ref@digest to stdout, so that
# IMAGE=$(uv run examples/detached.py ...) captures the image.

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys

from unikraft_cloud import (
    Build,
    UnikraftCloud,
    UnikraftCloudError,
    git_source,
    image_output,
    kraftfile_from,
)


async def main(args: argparse.Namespace) -> None:
    async with UnikraftCloud(build_url=args.server) as ukc:  # token from UKC_TOKEN
        src = git_source(args.git, args.ref or None, subdir=args.subdir or None)
        build = await ukc.builds.create(
            kraftfile=kraftfile_from(src),
            contexts={"context": src},
            output=[image_output(args.image)],
        )
        print(f"build {build.id}", file=sys.stderr)

        try:
            build = await follow(build)
        except asyncio.CancelledError:
            # Interrupted: the build would go on without us, so cancel it.
            await build.cancel()
            raise

        if build.result is None:
            # Failed or cancelled: the error is the build's, not the API's.
            print(f"build {build.id} {build.status}: {build.error}", file=sys.stderr)
            raise SystemExit(1)
        for img in build.result.images or []:
            print(f"{img.ref}@{img.digest}")


async def follow(build: Build) -> Build:
    """Print the build's progress as the service renders it, until it has ended."""
    while True:
        async with contextlib.aclosing(build.plain_logs()) as lines:
            async for text in lines:
                sys.stderr.write(text)
                sys.stderr.flush()
        build = await build.refresh()
        # The text ends when the build does, or when the service's side of the
        # stream broke off first; then it says so, and asking again replays it.
        if build.status not in ("waiting", "running"):
            return build


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a git repository on the remote build service and push it to <image>."
    )
    parser.add_argument("image", help="the image reference to push, including its tag")
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
    parser.add_argument(
        "--subdir",
        default="nginx",
        help="directory of the repository that holds the Kraftfile and is the build context, "
        "or empty for the root",
    )
    try:
        asyncio.run(main(parser.parse_args()))
    except KeyboardInterrupt:
        sys.exit(130)
    except UnikraftCloudError as err:
        print(f"API error ({err.status or '?'}): {err}", file=sys.stderr)
        raise SystemExit(1) from err
