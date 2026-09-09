# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

# `Volumes.list` shadows the builtin inside that class body, so annotations there
# spell the builtin out.
import builtins
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

from ..api.platform import models
from ..api.platform.volumes_gen import VolumesApi
from ..core.fanout import fanout
from ..core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from ..core.handle_set import HandleSet
from ..core.http import UNSET, CallOptions, TimeoutOption
from ..core.metro import MetroEndpoint, MetroScope
from ..core.pagination import paginate
from ..core.patch import PatchItem, ResourceEditor, to_patch_items
from ..core.resource import MetroGroup, Resource, ScopeOptions, first_tagged, list_tagged
from ..core.response import Ref, RefLike, describe_ref, or_absent, to_refs
from ..core.session import Session
from ._shared import (
    InstanceLike,
    at_metro,
    filter_of,
    name_or_uuid,
    options,
    ref_dict,
    resolved,
    scoped,
    tag_first,
)

__all__ = [
    "AttachedVolume",
    "DeletedVolume",
    "DetachedVolume",
    "UpdatedVolume",
    "Volume",
    "VolumeEditor",
    "VolumeHandle",
    "VolumeSet",
    "Volumes",
]

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)
V = TypeVar("V")

_KEY = "volumes"
_NOUN = "volume"


class Volume(models.Volume):
    """A persistent volume, tagged with the metro that served it."""

    metro: str


class DeletedVolume(models.DeleteVolumesResponseDeletedVolume):
    """What a delete reported, tagged with the metro that served it."""

    metro: str


class UpdatedVolume(models.UpdateVolumesResponseUpdatedVolume):
    """A volume as an update reports it back, tagged with its metro."""

    metro: str


class AttachedVolume(models.AttachVolumesResponseAttachedVolume):
    """What an attach reported, tagged with the metro that served it."""

    metro: str


class DetachedVolume(models.DetachVolumesResponseDetachedVolume):
    """What a detach reported, tagged with the metro that served it."""

    metro: str


#: A staged multi-operation edit of one volume.
VolumeEditor = ResourceEditor["VolumeHandle[UpdatedVolume]"]


class VolumeHandle(ResourceHandle[T]):
    """A chainable reference to one volume in one metro.

    .. code-block:: python

        await ukc.volumes.get(name="data").update(size_mb=2048)
        await ukc.volumes.get(name="data").attach(to="web", at="/data")
    """

    def __init__(self, volumes: Volumes, steps: HandleSteps[T]) -> None:
        super().__init__(steps)
        self._volumes = volumes

    def refresh(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeHandle[Volume]:
        """Re-read the volume's full details."""
        opts = options(headers, base_url, timeout)
        return self._then(lambda target: self._volumes.read(target, opts))

    def delete(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeHandle[DeletedVolume]:
        """Delete the volume."""
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> DeletedVolume:
            body = [models.NameOrUUID.model_validate(ref_dict(target.ref))]
            res = await self._volumes.api.delete_volumes(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, DeletedVolume, _NOUN)

        return self._then(run)

    def update(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **changes: Any,
    ) -> VolumeHandle[UpdatedVolume]:
        """Change the volume's properties and return the updated volume.

        .. code-block:: python

            await ukc.volumes.get(name="data").update(size_mb=2048, tags=["prod"])
        """
        return self.patch(
            to_patch_items(changes, "set"),
            headers=headers,
            base_url=base_url,
            timeout=timeout,
        )

    def patch(
        self,
        changes: Sequence[PatchItem],
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeHandle[UpdatedVolume]:
        """Apply update triples as the API models them."""
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> UpdatedVolume:
            body = [
                models.UpdateVolumesRequestItem.model_validate(
                    {**ref_dict(target.ref), "prop": item.prop, "op": item.op}
                    | ({} if item.value is None else {"value": item.value})
                )
                for item in changes
            ]
            res = await self._volumes.api.update_volumes(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, UpdatedVolume, _NOUN)

        return self._then(run)

    def edit(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeEditor:
        """Stage several operations and send them as one update."""
        return ResourceEditor(
            lambda items: self.patch(items, headers=headers, base_url=base_url, timeout=timeout),
            _NOUN,
        )

    def attach(
        self,
        *,
        to: InstanceLike,
        at: str,
        readonly: bool | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeHandle[AttachedVolume]:
        """Attach the volume to an instance at a mount point.

        ``to`` names the instance: a bare string is its name, and a
        :class:`~unikraft_cloud.Ref` says which identifier you hold.

        .. code-block:: python

            await ukc.volumes.get(name="data").attach(to="web", at="/data")
            await ukc.volumes.get(name="data").attach(
                to=Ref(uuid=inst.uuid), at="/data"
            )
        """
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> AttachedVolume:
            body = [
                models.AttachVolumesRequestItem.model_validate(
                    {**ref_dict(target.ref), "attach_to": name_or_uuid(to), "at": at}
                    | ({} if readonly is None else {"readonly": readonly})
                )
            ]
            res = await self._volumes.api.attach_volumes(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, AttachedVolume, _NOUN)

        return self._then(run)

    def detach(
        self,
        *,
        from_: InstanceLike | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeHandle[DetachedVolume]:
        """Detach the volume, optionally naming the instance to detach it from."""
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> DetachedVolume:
            body = [
                models.DetachVolumesRequestItem.model_validate(
                    {**ref_dict(target.ref)}
                    | ({} if from_ is None else {"from": name_or_uuid(from_)})
                )
            ]
            res = await self._volumes.api.detach_volumes(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, DetachedVolume, _NOUN)

        return self._then(run)

    def _then(self, fetch: Callable[[MetroTarget], Awaitable[V]]) -> VolumeHandle[V]:
        return VolumeHandle(self._volumes, self._chained(fetch))


class VolumeSet(HandleSet["VolumeHandle[Volume]", Volume]):
    """Every volume matching one reference, one per metro that holds it."""

    async def refresh(self, **opts: Any) -> list[Volume]:
        """Re-read every match's full details."""
        return await self._map(lambda handle: handle.refresh(**opts))

    async def delete(self, **opts: Any) -> list[DeletedVolume]:
        """Delete every match."""
        return await self._map(lambda handle: handle.delete(**opts))

    async def update(self, **changes: Any) -> list[UpdatedVolume]:
        """Apply the same changes to every match."""
        return await self._map(lambda handle: handle.update(**changes))

    def edit(self, **opts: Any) -> ResourceEditor[Awaitable[list[UpdatedVolume]]]:
        """Stage changes once and apply them to every match."""
        return ResourceEditor(
            lambda items: self._map(lambda handle: handle.patch(items, **opts)), _NOUN
        )

    async def attach(self, **opts: Any) -> list[AttachedVolume]:
        """Attach every match."""
        return await self._map(lambda handle: handle.attach(**opts))

    async def detach(self, **opts: Any) -> list[DetachedVolume]:
        """Detach every match."""
        return await self._map(lambda handle: handle.detach(**opts))


class Volumes(Resource[VolumesApi]):
    """Idiomatic client for Unikraft Cloud volumes."""

    noun = _NOUN

    def __init__(self, session: Session, scope: MetroScope) -> None:
        super().__init__(session, scope, VolumesApi(session.platform))

    def create(
        self,
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **spec: Any,
    ) -> VolumeHandle[Volume]:
        """Create a volume and return a handle to it.

        .. code-block:: python

            data = await ukc.metro("fra").volumes.create(name="data", size_mb=1024)
        """
        opts = scoped(options(headers, base_url, timeout), metros)
        body = models.CreateVolumeRequest.model_validate(spec)

        async def created() -> Located[Volume]:
            endpoint = await self._one_endpoint("Creating a volume", opts)
            res = await self.api.create_volume(body=body, **self._call(endpoint, opts))
            created_volume = first_tagged(
                res, _KEY, endpoint.metro, models.CreateVolumeResponseVolume, _NOUN
            )
            ref = (
                Ref(uuid=created_volume.uuid)
                if created_volume.uuid
                else Ref(name=created_volume.name)
            )
            target = MetroTarget(metro=endpoint.metro, base_url=endpoint.base_url, ref=ref)
            # A create reports less than a read does, so the handle reads the
            # volume rather than carrying the create's answer forward.
            return Located(target=target)

        return VolumeHandle(
            self,
            HandleSteps(
                locate=created,
                fetch=lambda target: self.read(target, opts),
                what="the volume being created",
            ),
        )

    def get(
        self,
        *,
        uuid: str | None = None,
        name: str | None = None,
        metro: str | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeHandle[Volume]:
        """Reference a single volume by ``name`` or ``uuid``."""
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = scoped(options(headers, base_url, timeout), metros)
        return VolumeHandle(
            self,
            HandleSteps(
                locate=lambda: self._locate(
                    ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
                ),
                fetch=lambda target: self.read(target, opts),
                what=f"volume {describe_ref(ref)}",
            ),
        )

    def each(
        self,
        *,
        uuid: str | None = None,
        name: str | None = None,
        metro: str | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> VolumeSet:
        """Reference every volume matching a name -- one per metro that holds it."""
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = scoped(options(headers, base_url, timeout), metros)

        async def locate() -> builtins.list[VolumeHandle[Volume]]:
            located = await self._locate_all(
                ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
            )
            return [
                VolumeHandle(
                    self,
                    HandleSteps(
                        locate=resolved(hit),
                        fetch=lambda target: self.read(target, opts),
                        what=f"volume {describe_ref(ref)}",
                    ),
                )
                for hit in located
            ]

        return VolumeSet(locate)

    def list(
        self,
        *,
        details: bool | None = None,
        tags: Sequence[str] | None = None,
        page_size: int | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> AsyncIterator[Volume]:
        """Lazily iterate every volume in scope, merging the metros as pages arrive."""
        opts = scoped(options(headers, base_url, timeout), metros)

        async def merged() -> AsyncIterator[Volume]:
            endpoints = await self._endpoints(opts)

            def per_metro(endpoint: MetroEndpoint) -> AsyncIterator[Volume]:
                async def fetch_page(count: int, start: str | None) -> builtins.list[Volume]:
                    res = await self.api.get_volumes(
                        count=count,
                        from_=start,
                        details=details,
                        tags=None if tags is None else builtins.list(tags),
                        **self._call(endpoint, opts),
                    )
                    return list_tagged(res, _KEY, endpoint.metro, Volume)

                return paginate(fetch_page, lambda vol: vol.uuid, page_size)

            async for volume in fanout(endpoints, per_metro):
                yield volume

        return merged()

    async def delete(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[DeletedVolume]:
        """Delete one or more volumes."""
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [models.NameOrUUID.model_validate(ref_dict(ref)) for ref in group.refs]
            return self.api.delete_volumes(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, DeletedVolume, call)

    async def read(self, target: MetroTarget, opts: CallOptions) -> Volume:
        """Read one volume's full details from the metro it was located in."""
        uuid, name = filter_of(target.ref)
        res = await self.api.get_volumes(
            uuid=uuid, name=name, details=True, **self._call(target, opts)
        )
        return tag_first(res, _KEY, target, Volume, _NOUN)

    async def _find(self, endpoint: MetroEndpoint, ref: Ref, opts: ScopeOptions) -> Volume | None:
        async def lookup() -> Volume | None:
            uuid, name = filter_of(ref)
            res = await self.api.get_volumes(
                uuid=uuid, name=name, details=True, **self._call(endpoint, opts)
            )
            entries = list_tagged(res, _KEY, endpoint.metro, Volume)
            return entries[0] if entries else None

        return await or_absent(lookup())

    async def _bulk(
        self,
        refs: RefLike | Sequence[RefLike],
        opts: ScopeOptions,
        cls: type[M],
        each: Callable[[MetroGroup], Awaitable[BaseModel]],
    ) -> builtins.list[M]:
        groups = await self._group_by_metro(
            to_refs(refs), opts, lambda endpoint, ref: self._find(endpoint, ref, opts)
        )

        async def run(group: MetroGroup) -> builtins.list[M]:
            return list_tagged(await each(group), _KEY, group.endpoint.metro, cls)

        return await self._run_groups(groups, run)
