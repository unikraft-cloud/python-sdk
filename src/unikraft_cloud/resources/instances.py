# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.

from __future__ import annotations

# `Instances.list` shadows the builtin inside that class body, so annotations
# there spell the builtin out.
import builtins
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from typing import Any, TypeVar, get_args

import httpx
from pydantic import BaseModel

from ..api.platform import models
from ..api.platform.instances_gen import InstancesApi
from ..core.errors import WaitTimeoutError
from ..core.fanout import fanout
from ..core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from ..core.handle_set import HandleSet
from ..core.http import UNSET, CallOptions, TimeoutOption, comma_separated
from ..core.metro import MetroEndpoint, MetroScope
from ..core.pagination import Listing, paginate
from ..core.patch import PatchItem, ResourceEditor, check_props, to_patch_items
from ..core.resource import (
    MetroGroup,
    Resource,
    ScopeOptions,
    check_spec,
    first_tagged,
    list_tagged,
    refs_matching,
)
from ..core.response import Ref, RefLike, describe_ref, matched_entries, or_absent
from ..core.session import Session
from ._shared import (
    at_metro,
    filter_of,
    filters_for,
    options,
    ref_dict,
    resolved,
    scoped,
    tag_first,
)

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
#: What a chained operation resolves to, model or list of them.
V = TypeVar("V")

#: The payload key every instance operation reports its results under.
_KEY = "instances"

#: How long a wait may outlast the timeout the API was given, in seconds.
_WAIT_MARGIN_SECONDS = 10


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


def _timed_out(res: BaseModel, wanted: str | None) -> None:
    """Report a wait that ran out of time as a timeout, not as any old failure.

    The API answers a lapsed wait with an error envelope that still carries the
    state it last saw, which is what a caller wants to know.
    """
    message = getattr(res, "message", None)
    if getattr(res, "status", None) != "error" or not isinstance(message, str):
        return
    if "timed out" not in message.lower():
        return
    entries = getattr(getattr(res, "data", None), _KEY, None) or []
    state = next((getattr(entry, "state", None) for entry in entries), None)
    error = WaitTimeoutError(
        f"Timed out waiting for the instance{f' to be {wanted!r}' if wanted else ''}"
        f"{f'; it is {state!r}.' if state else '.'}",
        kind="http",
        body=res,
    )
    error.state = state
    raise error


def _outlives(
    timeout: float | httpx.Timeout | None, seconds: int | None
) -> float | httpx.Timeout | None:
    """A timeout that outlasts a server-side wait of ``seconds``.

    The API holds the connection until the instance reaches the state or its own
    timeout elapses, so a shorter read timeout would cut the wait short.
    """
    current = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
    if current.read is None:
        return timeout
    read = None if seconds is None else max(current.read, seconds + _WAIT_MARGIN_SECONDS)
    return httpx.Timeout(connect=current.connect, read=read, write=current.write, pool=current.pool)


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
        opts = self._options(headers, base_url, timeout)
        return self._then(lambda target: self._instances.read(target, opts), opts)

    def start(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[StartedInstance]:
        """Start the instance."""
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> StartedInstance:
            body = [models.StartInstancesRequestItem.model_validate(ref_dict(target.ref))]
            res = await self._instances.api.start_instances(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, StartedInstance, "instance")

        return self._then(run, opts)

    def stop(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[StoppedInstance]:
        """Stop the instance."""
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> StoppedInstance:
            body = [models.StopInstancesRequestItem.model_validate(ref_dict(target.ref))]
            res = await self._instances.api.stop_instances(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, StoppedInstance, "instance")

        return self._then(run, opts)

    def suspend(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[SuspendedInstance]:
        """Suspend the instance."""
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> SuspendedInstance:
            body = [models.SuspendInstancesRequestItem.model_validate(ref_dict(target.ref))]
            res = await self._instances.api.suspend_instances(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, SuspendedInstance, "instance")

        return self._then(run, opts)

    def delete(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[DeletedInstance]:
        """Delete the instance."""
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> DeletedInstance:
            body = [models.DeleteInstanceRequestItem.model_validate(ref_dict(target.ref))]
            res = await self._instances.api.delete_instances(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, DeletedInstance, "instance")

        return self._then(run, opts)

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
        check_props(changes, get_args(models.MutableInstanceProperty), "instance")
        opts = self._options(headers, base_url, timeout)

        # Every triple carries the reference, so the body can only be built once
        # the metro -- and with it the reference to send -- is known.
        async def run(target: MetroTarget) -> UpdatedInstance:
            body = [
                models.UpdateInstancesRequestItem.model_validate(
                    {**ref_dict(target.ref), "prop": item.prop, "op": item.op}
                    | ({} if item.value is None else {"value": item.value})
                )
                for item in changes
            ]
            res = await self._instances.api.update_instances(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, UpdatedInstance, "instance")

        return self._then(run, opts)

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
        opts = self._options(headers, base_url, timeout)
        if "timeout" not in opts:
            opts["timeout"] = _outlives(self._instances.session.platform.timeout, timeout_seconds)

        async def run(target: MetroTarget) -> WaitedInstance:
            # The state and the timeout travel in the body: the API reads only an
            # identifier from the query here.
            body = [
                models.WaitInstancesRequestItem.model_validate(
                    ref_dict(target.ref)
                    | ({} if state is None else {"state": state})
                    | ({} if timeout_seconds is None else {"timeout_s": timeout_seconds})
                )
            ]
            res = await self._instances.api.wait_instances(body=body, **at_metro(target, opts))
            _timed_out(res, state)
            return tag_first(res, _KEY, target, WaitedInstance, "instance")

        return self._then(run, opts)

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
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> InstanceLogs:
            # As for `wait`, the range travels in the body rather than the query.
            body = [
                models.GetInstancesLogsRequestItem.model_validate(
                    ref_dict(target.ref)
                    | ({} if offset is None else {"offset": offset})
                    | ({} if limit is None else {"limit": limit})
                )
            ]
            res = await self._instances.api.get_instance_logs(body=body, **at_metro(target, opts))
            return tag_first(res, _KEY, target, InstanceLogs, "instance")

        return self._then(run, opts)

    def metrics(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[InstanceMetrics]:
        """Resource-usage metrics for the instance."""
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> InstanceMetrics:
            uuid, name = filter_of(target.ref)
            res = await self._instances.api.get_instance_metrics(
                uuid=uuid, name=name, **at_metro(target, opts)
            )
            return tag_first(res, _KEY, target, InstanceMetrics, "instance")

        return self._then(run, opts)

    def history(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[list[InstanceHistory]]:
        """The instance's state-change history."""
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> list[InstanceHistory]:
            uuid, name = filter_of(target.ref)
            res = await self._instances.api.get_instance_history(
                uuid=uuid, name=name, **at_metro(target, opts)
            )
            return list_tagged(res, _KEY, target.metro, InstanceHistory)

        return self._then(run, opts)

    def _then(
        self, fetch: Callable[[MetroTarget], Awaitable[V]], opts: CallOptions
    ) -> InstanceHandle[V]:
        """Chain another operation onto this handle."""
        return InstanceHandle(self._instances, self._chained(fetch, opts))


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
    key = _KEY

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

        Creation targets exactly one metro, so a client whose scope spans
        several must name one: ``ukc.metro("fra")`` or ``metros="fra"``.

        One call creates one instance. ``replicas`` creates several, which a
        single handle cannot reference, so it is refused here.

        .. code-block:: python

            web = await ukc.metro("fra").instances.create(
                image="nginx:latest", memory_mb=256
            )
        """
        call = options(headers, base_url, timeout)
        opts = scoped(call, metros)
        check_spec(spec, models.CreateInstanceRequest, self.noun)
        if spec.get("replicas"):
            raise TypeError(
                "`replicas` creates several instances, and this returns a handle to one. "
                "Call `create()` per instance, or create them in one request with "
                "`ukc.api.platform.instances.create_instance(...)`."
            )
        body = models.CreateInstanceRequest.model_validate(spec)

        async def created() -> Located[Instance]:
            endpoint = await self._one_endpoint("Creating an instance", opts)
            res = await self.api.create_instance(body=body, **self._call(endpoint, opts))
            instance = first_tagged(res, _KEY, endpoint.metro, Instance, "instance")
            ref = Ref(uuid=instance.uuid) if instance.uuid else Ref(name=instance.name)
            target = MetroTarget(metro=endpoint.metro, base_url=endpoint.base_url, ref=ref)
            # A create reports less than a read does, so the handle reads the
            # instance rather than carrying the create's answer forward.
            return Located(target=target)

        # The create itself is the locate step, so a chained operation waits for
        # it without a redundant read.
        return InstanceHandle(
            self,
            HandleSteps(
                locate=created,
                fetch=lambda target: self.read(target, opts),
                what="the instance being created",
                options=call,
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
        call = options(headers, base_url, timeout)
        opts = scoped(call, metros)
        return InstanceHandle(
            self,
            HandleSteps(
                locate=lambda: self._locate(
                    ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
                ),
                fetch=lambda target: self.read(target, opts),
                what=f"instance {describe_ref(ref)}",
                options=call,
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
        call = options(headers, base_url, timeout)
        opts = scoped(call, metros)

        async def locate() -> builtins.list[InstanceHandle[Instance]]:
            located = await self._locate_all(
                ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
            )
            return [
                InstanceHandle(
                    self,
                    HandleSteps(
                        locate=resolved(hit),
                        fetch=lambda target: self.read(target, opts),
                        what=f"instance {describe_ref(ref)}",
                        located=True,
                        options=call,
                    ),
                )
                for hit in located
            ]

        return InstanceSet(locate, f"instance {describe_ref(ref)}")

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
    ) -> Listing[Instance]:
        """Lazily iterate every instance in scope, or await it for a list.

        Each metro's pagination is followed and the metros are interleaved as
        their pages arrive; every instance carries the metro it came from. An
        instance matches `tags` only when it carries every one of them.

        If some metros fail, every healthy metro is drained first and a
        ``MetroFanoutError`` naming the failures is raised at the end.

        .. code-block:: python

            async for inst in ukc.instances.list(details=True):
                print(inst.metro, inst.name, inst.state)
            every = await ukc.instances.list(details=True)
        """
        opts = scoped(options(headers, base_url, timeout), metros)

        async def merged() -> AsyncIterator[Instance]:
            endpoints = await self._endpoints(opts)

            def per_metro(endpoint: MetroEndpoint) -> AsyncIterator[Instance]:
                async def fetch_page(count: int, start: str | None) -> builtins.list[Instance]:
                    res = await self.api.get_instances(
                        count=count,
                        from_=start,
                        details=details,
                        tags=comma_separated(tags),
                        **self._call(endpoint, opts),
                    )
                    return list_tagged(res, _KEY, endpoint.metro, Instance)

                return paginate(fetch_page, lambda inst: inst.uuid, page_size)

            async for instance in fanout(endpoints, per_metro):
                yield instance

        return Listing(merged())

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

        An instance the API could not delete raises, with the ones it did on the
        error's ``results``.

        References are located first when the scope spans metros, so each
        instance is deleted only in the metro that holds it.
        """
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.DeleteInstanceRequestItem.model_validate(ref_dict(ref)) for ref in group.refs
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
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.StartInstancesRequestItem.model_validate(ref_dict(ref)) for ref in group.refs
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
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.StopInstancesRequestItem.model_validate(ref_dict(ref)) for ref in group.refs
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
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.SuspendInstancesRequestItem.model_validate(ref_dict(ref))
                for ref in group.refs
            ]
            return self.api.suspend_instances(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, SuspendedInstance, call)

    async def read(self, target: MetroTarget, opts: CallOptions) -> Instance:
        """Read one instance's full details from the metro it was located in.

        Used by :class:`InstanceHandle`.
        """
        uuid, name = filter_of(target.ref)
        res = await self.api.get_instances(
            uuid=uuid, name=name, details=True, **self._call(target, opts)
        )
        return tag_first(res, _KEY, target, Instance, "instance")

    async def _find(self, endpoint: MetroEndpoint, ref: Ref, opts: ScopeOptions) -> Instance | None:
        """Look for one instance in one metro; absent is not a failure."""

        async def lookup() -> Instance | None:
            uuid, name = filter_of(ref)
            res = await self.api.get_instances(
                uuid=uuid, name=name, details=True, **self._call(endpoint, opts)
            )
            entries = list_tagged(res, _KEY, endpoint.metro, Instance)
            return entries[0] if entries else None

        return await or_absent(lookup())

    async def _match(
        self, endpoint: MetroEndpoint, refs: Sequence[Ref], opts: ScopeOptions
    ) -> builtins.list[Ref]:
        """Which of these references one metro holds, in a single filtered listing."""

        async def lookup() -> builtins.list[Ref]:
            uuid, name = filters_for(refs)
            res = await self.api.get_instances(uuid=uuid, name=name, **self._call(endpoint, opts))
            return refs_matching(refs, matched_entries(res, _KEY))

        return await or_absent(lookup()) or []
