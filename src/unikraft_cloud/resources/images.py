# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Images: what each metro's nodes have cached, from the platform API, and what
# the registry holds, from the control plane. The registry is what a node can
# pull from, so an existence check asks it, as the CLI's `images get` does.

from __future__ import annotations

# `Images.list` shadows the builtin inside that class body, so annotations
# there spell the builtin out.
import builtins
from collections.abc import Mapping

from ..api.platform import models
from ..api.platform.images_gen import ImagesApi
from ..core.fanout import MetroFailure, fanout_error, fanout_settled
from ..core.http import UNSET, TimeoutOption
from ..core.metro import MetroEndpoint, MetroScope
from ..core.resource import Resource, list_tagged
from ..core.session import Session
from ._shared import options, scoped

__all__ = ["Image", "Images"]

_KEY = "images"


class Image(models.Image):
    """An image a metro's nodes have cached, tagged with the metro that reported it."""

    metro: str


class Images(Resource[ImagesApi]):
    """Idiomatic client for the images an account can start instances from.

    Images are reported per metro, so an account-wide view asks every metro in
    scope and merges the answers; each image carries the metro it came from.
    Looking one up is a filtered listing, and a single metro's view is one
    metro's client: ``ukc.metro("fra").images.list(tag=...)``.
    """

    noun = "image"

    def __init__(self, session: Session, scope: MetroScope) -> None:
        super().__init__(session, scope, ImagesApi(session.platform))

    async def list(
        self,
        *,
        tag: str | None = None,
        digest: str | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[Image]:
        """The images in every metro in scope, optionally filtered.

        ``tag`` and ``digest`` narrow the listing the way the API does; both
        are passed on as given. The API answers a metro's whole listing in one
        page, so this returns a list rather than a listing to page through.

        .. code-block:: python

            for image in await ukc.images.list(tag="org/app:latest"):
                print(image.metro, image.url, image.size_in_bytes)
        """
        opts = scoped(options(headers, base_url, timeout), metros)
        endpoints = await self._endpoints(opts)

        async def per_metro(endpoint: MetroEndpoint) -> builtins.list[Image]:
            res = await self.api.get_images(tag=tag, digest=digest, **self._call(endpoint, opts))
            return list_tagged(res, _KEY, endpoint.metro, Image)

        if len(endpoints) == 1:
            return await per_metro(endpoints[0])

        outcomes = await fanout_settled(endpoints, per_metro)
        images: builtins.list[Image] = []
        failures: builtins.list[MetroFailure] = []
        for outcome in outcomes:
            if outcome.ok:
                images.extend(outcome.value)
            else:
                failures.append(MetroFailure(metro=outcome.endpoint.metro, error=outcome.error))
        if failures:
            error = fanout_error(len(endpoints), failures)
            # A partial answer is still an answer; carry what did arrive.
            error.results = list(images)
            raise error
        return images
