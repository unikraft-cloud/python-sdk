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
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from ..api.controlplane.images_gen import ImagesApi as RegistryApi
from ..api.platform import models
from ..api.platform.images_gen import ImagesApi
from ..core.fanout import MetroFailure, fanout_error, fanout_settled
from ..core.http import UNSET, TimeoutOption
from ..core.metro import MetroEndpoint, MetroScope
from ..core.resource import Resource, list_tagged
from ..core.response import envelope_entries
from ..core.session import Session
from ._shared import options, scoped

__all__ = ["Image", "Images", "RegistryImage"]

_KEY = "images"
#: The namespace a bare image name belongs to, as the CLI resolves one.
_DEFAULT_NAMESPACE = "official"
#: A digest is ``<algorithm>:<hex>``, as the OCI specification spells it.
_DIGEST = re.compile(r"^[a-z0-9]+(?:[.+_-][a-z0-9]+)*:[0-9a-f]+$", re.IGNORECASE)
#: A tag is a word, as the OCI specification spells it; an empty one is none.
_TAG = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


class Image(models.Image):
    """An image a metro's nodes have cached, tagged with the metro that reported it."""

    metro: str


@dataclass(frozen=True)
class RegistryImage:
    """One tag of an image in the registry, as the control plane reports it."""

    #: The repository, ``<namespace>/<name>``.
    repository: str
    #: The tag.
    tag: str
    #: The digest of the manifest the tag points at.
    digest: str | None = None
    #: The size of the image, in bytes.
    size: int | None = None
    #: When the tag was pushed.
    push_time: datetime | None = None

    @property
    def reference(self) -> str:
        """The image reference, ``<repository>:<tag>``."""
        return f"{self.repository}:{self.tag}"


@dataclass(frozen=True)
class _ImageRef:
    """Where in the registry an image reference points."""

    namespace: str
    repository: str
    tag: str | None
    digest: str | None


def _parse_ref(ref: str) -> _ImageRef:
    """Split ``[<registry>/][<namespace>/]<name>[:<tag>][@<digest>]`` into its parts.

    The reference is read as the CLI reads one: a scheme and a registry host
    are dropped, a bare name belongs to the ``official`` namespace, and neither
    a tag nor a digest means the ``latest`` tag.
    """
    rest = ref.split("://", 1)[-1]
    rest, at, digest = rest.partition("@")
    head, _, name = rest.rpartition("/")
    name, colon, tag = name.partition(":")
    segments = [segment for segment in head.split("/") if segment]
    # A registry host carries a dot or a port, or is `localhost`; a namespace
    # never does.
    if segments and ("." in segments[0] or ":" in segments[0] or segments[0] == "localhost"):
        segments = segments[1:]
    if not name:
        raise ValueError(
            f"An image reference names an image, `[<namespace>/]<name>[:<tag>]`; got {ref!r}."
        )
    if colon and not _TAG.match(tag):
        raise ValueError(
            f"An image tag is a word of letters, digits, `_`, `.` and `-`; got {tag!r} in {ref!r}."
        )
    if not segments:
        segments = [_DEFAULT_NAMESPACE]
    if at and not _DIGEST.match(digest):
        raise ValueError(f"An image digest is `<algorithm>:<hex>`; got {digest!r} in {ref!r}.")
    if not tag and not digest:
        tag = "latest"
    return _ImageRef(
        namespace=segments[0],
        repository="/".join([*segments, name]),
        tag=tag or None,
        digest=digest.lower() or None,
    )


class Images(Resource[ImagesApi]):
    """Idiomatic client for the images an account can start instances from.

    Images are reported per metro, so an account-wide view asks every metro in
    scope and merges the answers; each image carries the metro it came from.
    Looking one up is a filtered listing, and a single metro's view is one
    metro's client: ``ukc.metro("fra").images.list(tag=...)``.

    What the metros report is what their nodes have cached. Whether the
    registry holds an image at all -- and so whether a node can pull it -- is
    the control plane's to say, through :meth:`find` and :meth:`exists`.
    """

    noun = "image"

    def __init__(self, session: Session, scope: MetroScope) -> None:
        super().__init__(session, scope, ImagesApi(session.platform))
        self._registry = RegistryApi(session.control_plane)

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

    async def find(
        self,
        ref: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> RegistryImage | None:
        """The registry's record of an image, or ``None`` when it holds no such tag.

        ``ref`` is ``<namespace>/<name>:<tag>`` or ``<namespace>/<name>@<digest>``;
        with neither the tag is ``latest``, a bare name is in the ``official``
        namespace, and a registry host in front is ignored, as the CLI has it.
        The control plane answers from the registry itself, so a match is an
        image a node can pull -- unlike :meth:`list`, which reports what the
        nodes have cached. It lists the whole namespace to answer, so the cost
        grows with the namespace; a namespace the registry does not have holds
        no image.

        .. code-block:: python

            if await ukc.images.find("org/app:1.2.3") is None:
                build_and_push("org/app:1.2.3")
        """
        wanted = _parse_ref(ref)
        res = await self._registry.list_images(
            details=True, namespace=[wanted.namespace], headers=headers, timeout=timeout
        )
        for image in envelope_entries(res, _KEY):
            if image.name != wanted.repository:
                continue
            for tag in image.tags or []:
                if tag.name is None:
                    continue
                if wanted.tag is not None and tag.name != wanted.tag:
                    continue
                if wanted.digest is not None and (tag.digest or "").lower() != wanted.digest:
                    continue
                return RegistryImage(
                    repository=image.name,
                    tag=tag.name,
                    digest=tag.digest,
                    size=tag.size,
                    push_time=tag.push_time,
                )
        return None

    async def exists(
        self,
        ref: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> bool:
        """Whether the registry holds an image; see :meth:`find`."""
        return await self.find(ref, headers=headers, timeout=timeout) is not None
