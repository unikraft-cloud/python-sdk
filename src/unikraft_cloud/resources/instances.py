# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

# `Instances.list` shadows the builtin inside that class body, so annotations
# there spell the builtin out.
import builtins
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from ..api.platform import models
from ..api.platform.instances_gen import InstancesApi
from ..core.fanout import fanout
from ..core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from ..core.handle_set import HandleSet
from ..core.http import UNSET, CallOptions, TimeoutOption, Unset
from ..core.metro import MetroEndpoint, MetroScope
from ..core.pagination import paginate
from ..core.patch import PatchItem, ResourceEditor, to_patch_items
from ..core.resource import (
    MetroGroup,
    Resource,
    ScopeOptions,
    first_tagged,
    list_tagged,
)
from ..core.response import Ref, RefLike, describe_ref, or_absent, to_refs
from ..core.session import Session

__all__ = [
    "DeletedInstance",
    "Instance",
    "InstanceEditor",
    "InstanceHandle",
    "InstanceHistory",
    "InstanceLogs",
    "InstanceMetrics",
    "InstanceSet",
    "Instances",
    "StartedInstance",
    "StoppedInstance",
    "SuspendedInstance",
    "UpdatedInstance",
    "WaitedInstance",
]

#: What a handle resolves to, which is not always a single model: `history`
#: resolves to a list of them.
T = TypeVar("T")
#: A tagged model an operation reports.
M = TypeVar("M", bound=BaseModel)
#: What a chained operation resolves to, model or list of them.
V = TypeVar("V")

#: The payload key every instance operation reports its results under.
_KEY = "instances"


class Instance(models.Instance):
    """An instance (a microVM), tagged with the metro that served it."""

    metro: str


class StartedInstance(models.StartInstancesResponseStartedInstance):
    """What a start reported, tagged with the metro that served it."""

    metro: str


class StoppedInstance(models.StopInstancesResponseStoppedInstance):
    """What a stop reported, tagged with the metro that served it."""

    metro: str


class SuspendedInstance(models.SuspendInstancesResponseSuspendedInstance):
    """What a suspend reported, tagged with the metro that served it."""

    metro: str


class DeletedInstance(models.DeleteInstancesResponseInstance):
    """What a delete reported, tagged with the metro that served it."""

    metro: str


class UpdatedInstance(models.UpdateInstancesResponseUpdatedInstance):
    """An instance as an update reports it back, tagged with its metro."""

    metro: str


class WaitedInstance(models.WaitInstancesResponseWaitedInstance):
    """What the API observed while waiting, tagged with the metro that served it."""

    metro: str


class InstanceLogs(models.GetInstancesLogsResponseLoggedInstance):
    """An instance's console log, tagged with the metro that served it."""

    metro: str


class InstanceMetrics(models.GetInstancesMetricsResponseInstanceMetrics):
    """An instance's resource usage, tagged with the metro that served it."""

    metro: str


class InstanceHistory(models.GetCheckpointHistoryResponseInstanceHistory):
    """One entry of an instance's history, tagged with the metro that served it."""

    metro: str


#: A staged multi-operation edit of one instance.
InstanceEditor = ResourceEditor["InstanceHandle[UpdatedInstance]"]


def _options(
    headers: Mapping[str, str] | None,
    base_url: str | None,
    timeout: TimeoutOption,
) -> CallOptions:
    """Collect the per-call options an operation was given."""
    opts: CallOptions = {}
    if headers is not None:
        opts["headers"] = headers
    if base_url is not None:
        opts["base_url"] = base_url
    if not isinstance(timeout, Unset):
        opts["timeout"] = timeout
    return opts


def _scoped(opts: CallOptions, metros: MetroScope | None) -> ScopeOptions:
    # Every call option is also a scope option; the cast is what says so, since
    # TypedDicts do not widen on their own.
    scoped = cast("ScopeOptions", dict(opts))
    if metros is not None:
        scoped["metros"] = metros
    return scoped


def _at(target: MetroTarget, opts: CallOptions) -> CallOptions:
    """Point per-call options at the metro a handle resolved to."""
    return {**opts, "base_url": target.base_url}


def _ref_dict(ref: Ref) -> dict[str, str]:
    """A reference as a request-body item, without the metro it named.

    The metro says *where* to send the request, so it must not travel in the
    body -- the API rejects the unknown field.
    """
    return {"uuid": ref.uuid} if ref.uuid is not None else {"name": ref.name or ""}


def _filter(ref: Ref) -> tuple[builtins.list[str] | None, builtins.list[str] | None]:
    """The ``uuid`` and ``name`` query filters for a reference.

    Exactly one is set: the API validates whichever field it is given, so a name
    sent in the ``uuid`` filter fails outright.
    """
    if ref.uuid is not None:
        return [ref.uuid], None
    return None, [ref.name or ""]


def _tag(envelope: BaseModel, target: MetroTarget, cls: type[M]) -> M:
    """Unwrap a single-instance response and tag it with the metro it came from."""
    return first_tagged(envelope, _KEY, target.metro, cls, f"instance {describe_ref(target.ref)}")


class InstanceHandle(ResourceHandle[T]):
    """A chainable reference to one instance in one metro.

    Awaiting it yields the instance; calling an operation on it returns another
    handle, so operations compose without repeating the reference.

    Nothing is sent until the handle is awaited or an operation is chained onto
    it. With a single metro in scope, ``get(name=...).suspend()`` therefore
    performs one request; when the scope spans metros, the instance is located
    first so the operation reaches the metro that actually holds it.

    .. code-block:: python

        await ukc.instances.get(name="web").suspend()
        await (
            ukc.instances.create(image="nginx:latest")
            .wait(state="running")
            .logs(offset=-4096)
        )
    """

    def __init__(self, instances: Instances, steps: HandleSteps[T]) -> None:
        super().__init__(steps)
        self._instances = instances

    def refresh(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[Instance]:
        """Re-read the instance's full details."""
        opts = _options(headers, base_url, timeout)
        return self._then(lambda target: self._instances.read(target, opts))

    def start(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[StartedInstance]:
        """Start the instance."""
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> StartedInstance:
            body = [models.StartInstancesRequestItem.model_validate(_ref_dict(target.ref))]
            res = await self._instances.api.start_instances(body=body, **_at(target, opts))
            return _tag(res, target, StartedInstance)

        return self._then(run)

    def stop(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[StoppedInstance]:
        """Stop the instance."""
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> StoppedInstance:
            body = [models.StopInstancesRequestItem.model_validate(_ref_dict(target.ref))]
            res = await self._instances.api.stop_instances(body=body, **_at(target, opts))
            return _tag(res, target, StoppedInstance)

        return self._then(run)

    def suspend(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[SuspendedInstance]:
        """Suspend the instance."""
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> SuspendedInstance:
            body = [models.SuspendInstancesRequestItem.model_validate(_ref_dict(target.ref))]
            res = await self._instances.api.suspend_instances(body=body, **_at(target, opts))
            return _tag(res, target, SuspendedInstance)

        return self._then(run)

    def delete(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[DeletedInstance]:
        """Delete the instance."""
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> DeletedInstance:
            body = [models.DeleteInstanceRequestItem.model_validate(_ref_dict(target.ref))]
            res = await self._instances.api.delete_instances(body=body, **_at(target, opts))
            return _tag(res, target, DeletedInstance)

        return self._then(run)

    def update(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **changes: Any,
    ) -> InstanceHandle[UpdatedInstance]:
        """Change the instance's properties and return the updated instance.

        Pass a value to set it, or :data:`~unikraft_cloud.REMOVE` to remove the
        property; omitted properties are left alone.

        .. code-block:: python

            await ukc.instances.get(name="web").update(memory_mb=512, vcpus=2)
            await ukc.instances.get(name="web").update(env={"LOG_LEVEL": "debug"})
            await ukc.instances.get(name="web").update(autokill=REMOVE)
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
    ) -> InstanceHandle[UpdatedInstance]:
        """Apply update triples as the API models them, for what `update` cannot say."""
        opts = _options(headers, base_url, timeout)

        # Every triple carries the reference, so the body can only be built once
        # the metro -- and with it the reference to send -- is known.
        async def run(target: MetroTarget) -> UpdatedInstance:
            body = [
                models.UpdateInstancesRequestItem.model_validate(
                    {**_ref_dict(target.ref), "prop": item.prop, "op": item.op}
                    | ({} if item.value is None else {"value": item.value})
                )
                for item in changes
            ]
            res = await self._instances.api.update_instances(body=body, **_at(target, opts))
            return _tag(res, target, UpdatedInstance)

        return self._then(run)

    def edit(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceEditor:
        """Stage several operations and send them as one update.

        Use this when `update` is not enough -- merging into a property, or
        removing individual members.

        .. code-block:: python

            await (
                ukc.instances.get(name="web")
                .edit()
                .set(memory_mb=512)
                .add(env={"LOG_LEVEL": "debug"}, tags=["prod"])
                .delete(env=["OLD_FLAG"])
                .apply()
            )
        """
        return ResourceEditor(
            lambda items: self.patch(items, headers=headers, base_url=base_url, timeout=timeout),
            "instance",
        )

    def wait(
        self,
        *,
        state: models.InstanceState | None = None,
        timeout_seconds: int | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[WaitedInstance]:
        """Block until the instance reaches a state, and report what the API observed.

        The API fails the request if its own timeout elapses first, so this raises
        rather than returning.
        """
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> WaitedInstance:
            uuid, name = _filter(target.ref)
            res = await self._instances.api.wait_instances(
                uuid=uuid,
                name=name,
                state=None if state is None else [state],
                timeout_s=None if timeout_seconds is None else [timeout_seconds],
                **_at(target, opts),
            )
            return _tag(res, target, WaitedInstance)

        return self._then(run)

    def logs(
        self,
        *,
        offset: int | None = None,
        limit: int | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[InstanceLogs]:
        """Fetch the console log.

        The returned ``output`` is base64-encoded, as the API sends it. A negative
        ``offset`` is relative to the end of the log.

        .. code-block:: python

            logs = await ukc.instances.get(name="web").logs(offset=-4096)
            print(base64.b64decode(logs.output).decode())
        """
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> InstanceLogs:
            uuid, name = _filter(target.ref)
            res = await self._instances.api.get_instance_logs(
                uuid=uuid,
                name=name,
                offset=None if offset is None else [offset],
                limit=None if limit is None else [limit],
                **_at(target, opts),
            )
            return _tag(res, target, InstanceLogs)

        return self._then(run)

    def metrics(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[InstanceMetrics]:
        """Resource-usage metrics for the instance."""
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> InstanceMetrics:
            uuid, name = _filter(target.ref)
            res = await self._instances.api.get_instance_metrics(
                uuid=uuid, name=name, **_at(target, opts)
            )
            return _tag(res, target, InstanceMetrics)

        return self._then(run)

    def history(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[list[InstanceHistory]]:
        """The instance's state-change history."""
        opts = _options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> list[InstanceHistory]:
            uuid, name = _filter(target.ref)
            res = await self._instances.api.get_instance_history(
                uuid=uuid, name=name, **_at(target, opts)
            )
            return list_tagged(res, _KEY, target.metro, InstanceHistory)

        return self._then(run)

    def _then(self, fetch: Callable[[MetroTarget], Awaitable[V]]) -> InstanceHandle[V]:
        """Chain another operation onto this handle."""
        return InstanceHandle(self._instances, self._chained(fetch))


class InstanceSet(HandleSet["InstanceHandle[Instance]", Instance]):
    """Every instance matching one reference, one per metro that holds it.

    Operations run in all of them concurrently and return one result per metro.

    .. code-block:: python

        await ukc.instances.each(name="web").suspend()
        for inst in await ukc.instances.each(name="web"):
            print(inst.metro)
    """

    async def refresh(self, **opts: Any) -> list[Instance]:
        """Re-read every match's full details."""
        return await self._map(lambda handle: handle.refresh(**opts))

    async def start(self, **opts: Any) -> list[StartedInstance]:
        """Start every match."""
        return await self._map(lambda handle: handle.start(**opts))

    async def stop(self, **opts: Any) -> list[StoppedInstance]:
        """Stop every match."""
        return await self._map(lambda handle: handle.stop(**opts))

    async def suspend(self, **opts: Any) -> list[SuspendedInstance]:
        """Suspend every match."""
        return await self._map(lambda handle: handle.suspend(**opts))

    async def delete(self, **opts: Any) -> list[DeletedInstance]:
        """Delete every match."""
        return await self._map(lambda handle: handle.delete(**opts))

    async def update(self, **changes: Any) -> list[UpdatedInstance]:
        """Apply the same changes to every match."""
        return await self._map(lambda handle: handle.update(**changes))

    def edit(self, **opts: Any) -> ResourceEditor[Awaitable[list[UpdatedInstance]]]:
        """Stage changes once and apply them to every match."""
        return ResourceEditor(
            lambda items: self._map(lambda handle: handle.patch(items, **opts)),
            "instance",
        )

    async def wait(self, **opts: Any) -> list[WaitedInstance]:
        """Wait for every match to reach a state."""
        return await self._map(lambda handle: handle.wait(**opts))

    async def logs(self, **opts: Any) -> list[InstanceLogs]:
        """Fetch every match's console log."""
        return await self._map(lambda handle: handle.logs(**opts))

    async def metrics(self, **opts: Any) -> list[InstanceMetrics]:
        """Resource-usage metrics for every match."""
        return await self._map(lambda handle: handle.metrics(**opts))

    async def history(self, **opts: Any) -> list[list[InstanceHistory]]:
        """State-change history for every match."""
        return await self._map(lambda handle: handle.history(**opts))


class Instances(Resource[InstancesApi]):
    """Idiomatic client for Unikraft Cloud instances.

    Envelope-free results, automatic pagination, and metro fan-out.
    Single-instance operations return a chainable :class:`InstanceHandle`.

    The raw, fully-typed plumbing for this resource stays available on ``api``.
    """

    noun = "instance"

    def __init__(self, session: Session, scope: MetroScope) -> None:
        super().__init__(session, scope, InstancesApi(session.platform))

    def create(
        self,
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **spec: Any,
    ) -> InstanceHandle[Instance]:
        """Create an instance and return a handle to it.

        Creation targets exactly one metro: the client's, or the default metro
        when the scope spans several.

        .. code-block:: python

            web = await ukc.metro("fra").instances.create(
                image="nginx:latest", memory_mb=256
            )
        """
        opts = _scoped(_options(headers, base_url, timeout), metros)
        body = models.CreateInstanceRequest.model_validate(spec)

        async def created() -> Located[Instance]:
            endpoint = await self._one_endpoint("Creating an instance", opts)
            res = await self.api.create_instance(body=body, **self._call(endpoint, opts))
            instance = first_tagged(res, _KEY, endpoint.metro, Instance, "instance")
            ref = Ref(uuid=instance.uuid) if instance.uuid else Ref(name=instance.name)
            target = MetroTarget(metro=endpoint.metro, base_url=endpoint.base_url, ref=ref)
            return Located(target=target, value=instance)

        # The create itself is the locate step, so a chained operation waits for
        # it without a redundant read.
        return InstanceHandle(
            self,
            HandleSteps(
                locate=created,
                fetch=lambda target: self.read(target, opts),
                what="the instance being created",
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
    ) -> InstanceHandle[Instance]:
        """Reference a single instance by ``name`` or ``uuid``.

        Await the handle to read the instance, or chain an operation onto it.

        .. code-block:: python

            web = await ukc.instances.get(name="web")
            await ukc.instances.get(name="web", metro="fra").suspend()
        """
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = _scoped(_options(headers, base_url, timeout), metros)
        return InstanceHandle(
            self,
            HandleSteps(
                locate=lambda: self._locate(
                    ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
                ),
                fetch=lambda target: self.read(target, opts),
                what=f"instance {describe_ref(ref)}",
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
    ) -> InstanceSet:
        """Reference every instance matching a name -- one per metro that holds it.

        A name can exist in several metros at once; this addresses all of them,
        where :meth:`get` insists you pick one.

        .. code-block:: python

            await ukc.instances.each(name="web").suspend()  # in every metro
            [inst.metro for inst in await ukc.instances.each(name="web")]
        """
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = _scoped(_options(headers, base_url, timeout), metros)

        async def locate() -> builtins.list[InstanceHandle[Instance]]:
            located = await self._locate_all(
                ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
            )
            return [
                InstanceHandle(
                    self,
                    HandleSteps(
                        locate=_already(hit),
                        fetch=lambda target: self.read(target, opts),
                        what=f"instance {describe_ref(ref)}",
                    ),
                )
                for hit in located
            ]

        return InstanceSet(locate)

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
    ) -> AsyncIterator[Instance]:
        """Lazily iterate every instance in scope.

        Each metro's pagination is followed and the metros are interleaved as
        their pages arrive; every instance carries the metro it came from.

        If some metros fail, every healthy metro is drained first and a
        ``MetroFanoutError`` naming the failures is raised at the end.

        .. code-block:: python

            async for inst in ukc.instances.list(details=True):
                print(inst.metro, inst.name, inst.state)
        """
        opts = _scoped(_options(headers, base_url, timeout), metros)

        async def merged() -> AsyncIterator[Instance]:
            endpoints = await self._endpoints(opts)

            def per_metro(endpoint: MetroEndpoint) -> AsyncIterator[Instance]:
                async def fetch_page(count: int, start: str | None) -> builtins.list[Instance]:
                    res = await self.api.get_instances(
                        count=count,
                        from_=start,
                        details=details,
                        tags=None if tags is None else builtins.list(tags),
                        **self._call(endpoint, opts),
                    )
                    return list_tagged(res, _KEY, endpoint.metro, Instance)

                return paginate(fetch_page, lambda inst: inst.uuid, page_size)

            async for instance in fanout(endpoints, per_metro):
                yield instance

        return merged()

    async def delete(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[DeletedInstance]:
        """Delete one or more instances.

        References are located first when the scope spans metros, so each
        instance is deleted only in the metro that holds it.
        """
        opts = _scoped(_options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.DeleteInstanceRequestItem.model_validate(_ref_dict(ref))
                for ref in group.refs
            ]
            return self.api.delete_instances(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, DeletedInstance, call)

    async def start(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[StartedInstance]:
        """Start one or more instances."""
        opts = _scoped(_options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.StartInstancesRequestItem.model_validate(_ref_dict(ref))
                for ref in group.refs
            ]
            return self.api.start_instances(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, StartedInstance, call)

    async def stop(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[StoppedInstance]:
        """Stop one or more instances."""
        opts = _scoped(_options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.StopInstancesRequestItem.model_validate(_ref_dict(ref)) for ref in group.refs
            ]
            return self.api.stop_instances(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, StoppedInstance, call)

    async def suspend(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[SuspendedInstance]:
        """Suspend one or more instances."""
        opts = _scoped(_options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.SuspendInstancesRequestItem.model_validate(_ref_dict(ref))
                for ref in group.refs
            ]
            return self.api.suspend_instances(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, SuspendedInstance, call)

    async def read(self, target: MetroTarget, opts: CallOptions) -> Instance:
        """Read one instance's full details from the metro it was located in.

        Used by :class:`InstanceHandle`.
        """
        uuid, name = _filter(target.ref)
        res = await self.api.get_instances(
            uuid=uuid, name=name, details=True, **self._call(target, opts)
        )
        return _tag(res, target, Instance)

    async def _find(self, endpoint: MetroEndpoint, ref: Ref, opts: ScopeOptions) -> Instance | None:
        """Look for one instance in one metro; absent is not a failure."""

        async def lookup() -> Instance | None:
            uuid, name = _filter(ref)
            res = await self.api.get_instances(
                uuid=uuid, name=name, details=True, **self._call(endpoint, opts)
            )
            entries = list_tagged(res, _KEY, endpoint.metro, Instance)
            return entries[0] if entries else None

        return await or_absent(lookup())

    async def _bulk(
        self,
        refs: RefLike | Sequence[RefLike],
        opts: ScopeOptions,
        cls: type[M],
        each: Callable[[MetroGroup], Awaitable[BaseModel]],
    ) -> builtins.list[M]:
        """Run a bulk operation once per metro group and tag every result."""
        groups = await self._group_by_metro(
            to_refs(refs), opts, lambda endpoint, ref: self._find(endpoint, ref, opts)
        )

        async def run(group: MetroGroup) -> builtins.list[M]:
            return list_tagged(await each(group), _KEY, group.endpoint.metro, cls)

        return await self._run_groups(groups, run)


def _already(hit: Located[Instance]) -> Callable[[], Awaitable[Located[Instance]]]:
    """A locate step for a match that has already been found."""

    async def located() -> Located[Instance]:
        return hit

    return located
