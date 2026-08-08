# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

# `ServiceGroups.list` shadows the builtin inside that class body, so annotations
# there spell the builtin out.
import builtins
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

from ..api.platform import models
from ..api.platform.service_groups_gen import ServiceGroupsApi
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
from ._shared import at_metro, filter_of, options, ref_dict, resolved, scoped, tag_first

__all__ = [
    "DeletedServiceGroup",
    "ServiceGroup",
    "ServiceGroupEditor",
    "ServiceGroupHandle",
    "ServiceGroupSet",
    "ServiceGroups",
    "UpdatedServiceGroup",
]

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)
V = TypeVar("V")

_KEY = "service_groups"
_NOUN = "service group"


class ServiceGroup(models.ServiceGroup):
    """A service group (load-balanced networking), tagged with its metro."""

    metro: str


class DeletedServiceGroup(models.DeleteServiceGroupsResponseDeletedServiceGroup):
    """What a delete reported, tagged with the metro that served it."""

    metro: str


class UpdatedServiceGroup(models.UpdateServiceGroupsResponseUpdatedServiceGroup):
    """A service group as an update reports it back, tagged with its metro."""

    metro: str


#: A staged multi-operation edit of one service group.
ServiceGroupEditor = ResourceEditor["ServiceGroupHandle[UpdatedServiceGroup]"]


class ServiceGroupHandle(ResourceHandle[T]):
    """A chainable reference to one service group in one metro."""

    def __init__(self, services: ServiceGroups, steps: HandleSteps[T]) -> None:
        super().__init__(steps)
        self._services = services

    def refresh(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> ServiceGroupHandle[ServiceGroup]:
        """Re-read the service group's full details."""
        opts = options(headers, base_url, timeout)
        return self._then(lambda target: self._services.read(target, opts))

    def delete(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> ServiceGroupHandle[DeletedServiceGroup]:
        """Delete the service group."""
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> DeletedServiceGroup:
            body = [models.NameOrUUID.model_validate(ref_dict(target.ref))]
            res = await self._services.api.delete_service_groups(
                body=body, **at_metro(target, opts)
            )
            return tag_first(res, _KEY, target, DeletedServiceGroup, _NOUN)

        return self._then(run)

    def update(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **changes: Any,
    ) -> ServiceGroupHandle[UpdatedServiceGroup]:
        """Change the service group's properties and return the updated group.

        .. code-block:: python

            await ukc.services.get(name="web").update(hard_limit=10)
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
    ) -> ServiceGroupHandle[UpdatedServiceGroup]:
        """Apply update triples as the API models them."""
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> UpdatedServiceGroup:
            body = [
                models.UpdateServiceGroupsRequestItem.model_validate(
                    {**ref_dict(target.ref), "prop": item.prop, "op": item.op}
                    | ({} if item.value is None else {"value": item.value})
                )
                for item in changes
            ]
            res = await self._services.api.update_service_groups(
                body=body, **at_metro(target, opts)
            )
            return tag_first(res, _KEY, target, UpdatedServiceGroup, _NOUN)

        return self._then(run)

    def edit(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> ServiceGroupEditor:
        """Stage several operations and send them as one update."""
        return ResourceEditor(
            lambda items: self.patch(items, headers=headers, base_url=base_url, timeout=timeout),
            _NOUN,
        )

    def _then(self, fetch: Callable[[MetroTarget], Awaitable[V]]) -> ServiceGroupHandle[V]:
        return ServiceGroupHandle(self._services, self._chained(fetch))


class ServiceGroupSet(HandleSet["ServiceGroupHandle[ServiceGroup]", ServiceGroup]):
    """Every service group matching one reference, one per metro that holds it."""

    async def refresh(self, **opts: Any) -> list[ServiceGroup]:
        """Re-read every match's full details."""
        return await self._map(lambda handle: handle.refresh(**opts))

    async def delete(self, **opts: Any) -> list[DeletedServiceGroup]:
        """Delete every match."""
        return await self._map(lambda handle: handle.delete(**opts))

    async def update(self, **changes: Any) -> list[UpdatedServiceGroup]:
        """Apply the same changes to every match."""
        return await self._map(lambda handle: handle.update(**changes))

    def edit(self, **opts: Any) -> ResourceEditor[Awaitable[list[UpdatedServiceGroup]]]:
        """Stage changes once and apply them to every match."""
        return ResourceEditor(
            lambda items: self._map(lambda handle: handle.patch(items, **opts)), _NOUN
        )


class ServiceGroups(Resource[ServiceGroupsApi]):
    """Idiomatic client for Unikraft Cloud service groups."""

    noun = _NOUN

    def __init__(self, session: Session, scope: MetroScope) -> None:
        super().__init__(session, scope, ServiceGroupsApi(session.platform))

    def create(
        self,
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **spec: Any,
    ) -> ServiceGroupHandle[ServiceGroup]:
        """Create a service group and return a handle to it."""
        opts = scoped(options(headers, base_url, timeout), metros)
        body = models.CreateServiceGroupRequest.model_validate(spec)

        async def created() -> Located[ServiceGroup]:
            endpoint = await self._one_endpoint("Creating a service group", opts)
            res = await self.api.create_service_group(body=body, **self._call(endpoint, opts))
            group = first_tagged(res, _KEY, endpoint.metro, ServiceGroup, _NOUN)
            ref = Ref(uuid=group.uuid) if group.uuid else Ref(name=group.name)
            target = MetroTarget(metro=endpoint.metro, base_url=endpoint.base_url, ref=ref)
            return Located(target=target, value=group)

        return ServiceGroupHandle(
            self,
            HandleSteps(
                locate=created,
                fetch=lambda target: self.read(target, opts),
                what="the service group being created",
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
    ) -> ServiceGroupHandle[ServiceGroup]:
        """Reference a single service group by ``name`` or ``uuid``."""
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = scoped(options(headers, base_url, timeout), metros)
        return ServiceGroupHandle(
            self,
            HandleSteps(
                locate=lambda: self._locate(
                    ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
                ),
                fetch=lambda target: self.read(target, opts),
                what=f"service group {describe_ref(ref)}",
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
    ) -> ServiceGroupSet:
        """Reference every service group matching a name -- one per metro."""
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = scoped(options(headers, base_url, timeout), metros)

        async def locate() -> builtins.list[ServiceGroupHandle[ServiceGroup]]:
            located = await self._locate_all(
                ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
            )
            return [
                ServiceGroupHandle(
                    self,
                    HandleSteps(
                        locate=resolved(hit),
                        fetch=lambda target: self.read(target, opts),
                        what=f"service group {describe_ref(ref)}",
                    ),
                )
                for hit in located
            ]

        return ServiceGroupSet(locate)

    def list(
        self,
        *,
        details: bool | None = None,
        page_size: int | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> AsyncIterator[ServiceGroup]:
        """Lazily iterate every service group in scope, merging the metros."""
        opts = scoped(options(headers, base_url, timeout), metros)

        async def merged() -> AsyncIterator[ServiceGroup]:
            endpoints = await self._endpoints(opts)

            def per_metro(endpoint: MetroEndpoint) -> AsyncIterator[ServiceGroup]:
                async def fetch_page(count: int, start: str | None) -> builtins.list[ServiceGroup]:
                    res = await self.api.get_service_groups(
                        count=count,
                        from_=start,
                        details=details,
                        **self._call(endpoint, opts),
                    )
                    return list_tagged(res, _KEY, endpoint.metro, ServiceGroup)

                return paginate(fetch_page, lambda group: group.uuid, page_size)

            async for group in fanout(endpoints, per_metro):
                yield group

        return merged()

    async def delete(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[DeletedServiceGroup]:
        """Delete one or more service groups."""
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [models.NameOrUUID.model_validate(ref_dict(ref)) for ref in group.refs]
            return self.api.delete_service_groups(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, DeletedServiceGroup, call)

    async def read(self, target: MetroTarget, opts: CallOptions) -> ServiceGroup:
        """Read one service group's full details from the metro it was located in."""
        uuid, name = filter_of(target.ref)
        res = await self.api.get_service_groups(
            uuid=uuid, name=name, details=True, **self._call(target, opts)
        )
        return tag_first(res, _KEY, target, ServiceGroup, _NOUN)

    async def _find(
        self, endpoint: MetroEndpoint, ref: Ref, opts: ScopeOptions
    ) -> ServiceGroup | None:
        async def lookup() -> ServiceGroup | None:
            uuid, name = filter_of(ref)
            res = await self.api.get_service_groups(
                uuid=uuid, name=name, details=True, **self._call(endpoint, opts)
            )
            entries = list_tagged(res, _KEY, endpoint.metro, ServiceGroup)
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
