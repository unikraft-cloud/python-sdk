# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.

from __future__ import annotations

# `Instances.list` shadows the builtin inside that class body, so annotations
# there spell the builtin out.
import asyncio
import builtins
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any, Literal, TypeGuard, TypeVar, get_args, overload

import httpx
from pydantic import BaseModel

from ..api.platform import models
from ..api.platform.instances_gen import InstancesApi
from ..core.errors import NotFoundError, ResponseError, UnikraftCloudError, WaitTimeoutError
from ..core.fanout import MetroFanoutError, fanout
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
from ..plugins import Plugin, ResolvedInstance
from ..plugins.sandbox import PLUGIN_NAME, Sandbox
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
from .stop import Stop, StopReason

__all__ = [
    "DeletedInstance",
    "Instance",
    "InstanceEditor",
    "InstanceHandle",
    "InstanceHistory",
    "InstanceLogs",
    "InstanceMetrics",
    "InstanceSet",
    "InstanceStoppedError",
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

    @property
    def stop(self) -> Stop | None:
        """Why the instance stopped, decoded; ``None`` while the API reports no reason."""
        if self.stop_reason is None:
            return None
        return Stop(StopReason(self.stop_reason), self.stop_code)

    def describe_stop(self) -> str:
        """Why the instance stopped, in words; empty while the API reports no reason."""
        stop = self.stop
        return "" if stop is None else str(stop)


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

#: How long the first retry of a busy delete waits, and the most any retry waits.
_BUSY_RETRY_INTERVAL = 0.5
_BUSY_RETRY_MAX_INTERVAL = 2.0
#: How the API reports a resource something else still holds: ``EBUSY``, by
#: its errno name or as the bare Linux value.
_BUSY = re.compile(r"\bEBUSY\b|Unknown error -16\b")

# Named so tests can stand in for it and assert the backoff without waiting.
_sleep = asyncio.sleep


class InstanceStoppedError(UnikraftCloudError):
    """An instance stopped instead of running.

    :meth:`Instances.create` raises this when the instance it made stopped
    before it was running -- a node could not pull its image, say, or its kernel
    crashed. The instance is read back so that the reason travels with the
    error, and it is left as it is: read its console log, or delete it. One
    gone already -- deleted on stop, say -- is described from the failed item
    alone, with no reason to give.

    .. code-block:: python

        try:
            web = await fra.instances.create(image="org/app:latest", autostart=True, timeout_s=30)
        except InstanceStoppedError as err:
            print(err.stop)  # e.g. "platform stop: image pull failed"
            await fra.instances.get(uuid=err.instance.uuid).delete()
    """

    #: The instance, as it was read after it stopped, or as the failed item
    #: described it when it was gone already.
    instance: Instance

    def __init__(
        self,
        message: str,
        *,
        instance: Instance,
        errors: tuple[ResponseError, ...] | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message, kind="http", errors=errors, body=body)
        self.instance = instance

    @property
    def stop(self) -> Stop | None:
        """Why it stopped, decoded, when the platform says."""
        return self.instance.stop


def _is_busy(err: UnikraftCloudError) -> bool:
    """Whether a failure says the resource is still in use, and so worth retrying."""
    messages = [str(err), *(error.message or "" for error in err.errors or ())]
    return any(_BUSY.search(message) for message in messages)


async def _while_busy(attempt: Callable[[], Awaitable[V]], retry_busy: float | None) -> V:
    """Run ``attempt``, retrying with backoff for ``retry_busy`` seconds while it reports busy."""
    if retry_busy is None:
        return await attempt()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + retry_busy
    interval = _BUSY_RETRY_INTERVAL
    while True:
        try:
            return await attempt()
        except UnikraftCloudError as err:
            remaining = deadline - loop.time()
            if remaining <= 0 or not _is_busy(err):
                raise
        await _sleep(min(interval, remaining))
        interval = min(interval * 2, _BUSY_RETRY_MAX_INTERVAL)


def _ref_of(instance: models.Instance) -> Ref:
    """The reference to address an instance the API reported by, its UUID first."""
    return Ref(uuid=instance.uuid) if instance.uuid else Ref(name=instance.name)


def _timed_out(res: BaseModel, wanted: str | None) -> None:
    """Report a wait that ran out of time as a timeout, not as any old failure.

    The API answers a lapsed wait with an error envelope that still carries the
    state it last saw, which is what a caller wants to know, and names the
    instances, which travel on ``errors``: a create whose wait lapsed still
    hands over the instance it made.
    """
    message = getattr(res, "message", None)
    if getattr(res, "status", None) != "error" or not isinstance(message, str):
        return
    if "timed out" not in message.lower():
        return
    state = _first_state(res)
    entries = getattr(getattr(res, "data", None), _KEY, None) or []
    errors = tuple(
        ResponseError(
            uuid=getattr(entry, "uuid", None),
            name=getattr(entry, "name", None),
            state=getattr(entry, "state", None),
        )
        for entry in entries
    )
    error = WaitTimeoutError(
        f"Timed out waiting for the instance{f' to be {wanted!r}' if wanted else ''}"
        f"{f'; it is {state!r}.' if state else '.'}",
        kind="http",
        errors=errors or None,
        body=res,
    )
    error.state = state
    raise error


def _first_state(res: BaseModel) -> str | None:
    """The state the first reported item is in, when the response names one."""
    entries = getattr(getattr(res, "data", None), _KEY, None) or []
    return next((getattr(entry, "state", None) for entry in entries), None)


def _create_wait_seconds(spec: Mapping[str, Any]) -> float | None:
    """How long a create asks the API to wait for the instance to run, in seconds.

    ``timeout_s`` wins; the deprecated ``wait_timeout_ms`` is read when it is
    the only one given, rounded up to whole seconds. ``None`` is a create that
    does not wait; less than zero, one that waits as long as the API lets it.
    """
    seconds = spec.get("timeout_s")
    if _is_number(seconds):
        return seconds
    millis = spec.get("wait_timeout_ms")
    if _is_number(millis):
        return -(-millis // 1000) if millis >= 0 else -1
    return None


def _is_number(value: Any) -> TypeGuard[float]:
    """Whether a value is a number the API takes as seconds; a bool is none."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _outlives(
    timeout: float | httpx.Timeout | None, seconds: float | None
) -> float | httpx.Timeout | None:
    """A timeout that outlasts a server-side wait of ``seconds``.

    The API holds the connection until the instance reaches the state or its own
    timeout elapses, so a shorter read timeout would cut the wait short. A wait
    of ``None``, or of less than zero, is one only the API bounds, so the read
    is unbounded too; a wait of zero is none, so the timeout stands.
    """
    current = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
    if current.read is None or seconds == 0:
        return timeout
    if seconds is None or seconds < 0:
        read = None
    else:
        read = max(current.read, seconds + _WAIT_MARGIN_SECONDS)
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

    @overload
    def delete(
        self,
        *,
        timeout_seconds: int | None = None,
        retry_busy: float | None = None,
        missing_ok: Literal[False] = False,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[DeletedInstance]: ...

    @overload
    def delete(
        self,
        *,
        timeout_seconds: int | None = None,
        retry_busy: float | None = None,
        missing_ok: Literal[True],
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[DeletedInstance | None]: ...

    def delete(
        self,
        *,
        timeout_seconds: int | None = None,
        retry_busy: float | None = None,
        missing_ok: bool = False,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> InstanceHandle[Any]:
        """Delete the instance, stopping it first if it runs.

        ``timeout_seconds`` blocks until the instance is gone, or for that long;
        ``-1`` waits for as long as the platform allows. Without it the API
        answers as soon as the deletion is under way. The read timeout is
        stretched to outlast the wait only when no ``timeout`` was given, here
        or to the handle.

        With ``missing_ok`` an instance that is not there -- gone already, or
        never found -- resolves to ``None`` instead of raising
        :class:`NotFoundError`.

        ``retry_busy`` keeps trying for that many seconds, backing off in
        between, while the API reports the instance as busy. Something another
        instance held on to -- a relay interface, for one -- stays busy for a
        while after that instance is deleted.

        .. code-block:: python

            await ukc.instances.get(name="web").delete(timeout_seconds=-1)
            await ukc.instances.get(name="relay").delete(retry_busy=20, missing_ok=True)
        """
        opts = self._options(headers, base_url, timeout)
        if timeout_seconds is not None and "timeout" not in opts:
            opts["timeout"] = _outlives(self._instances.session.platform.timeout, timeout_seconds)
        extra = {} if timeout_seconds is None else {"timeout_s": timeout_seconds}

        async def attempt(target: MetroTarget) -> DeletedInstance | None:
            body = [models.DeleteInstanceRequestItem.model_validate(ref_dict(target.ref) | extra)]
            try:
                res = await self._instances.api.delete_instances(
                    body=body, **at_metro(target, opts)
                )
                return tag_first(res, _KEY, target, DeletedInstance, "instance")
            except NotFoundError as err:
                # The API losing the instance is forgiven; a route that is not there is not.
                if not missing_ok or not err.absent:
                    raise
                return None

        async def run(target: MetroTarget) -> DeletedInstance | None:
            return await _while_busy(lambda: attempt(target), retry_busy)

        steps = self._chained(run, opts)
        if missing_ok:
            # An instance no metro holds is as gone as one the API just lost.
            steps = replace(steps, absent=lambda: None)
        return InstanceHandle(self._instances, steps)

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

    def plugin(self, name: str) -> Plugin:
        """A plugin attached to the instance, addressed lazily.

        Nothing is sent until the plugin's route is needed. Resolving it runs
        this handle's own operation first, if it is one, and reads the instance
        only when its UUID is not yet known: a UUID reference, a located or
        created instance, and a waited-for instance all already know it.

        .. code-block:: python

            route = await ukc.instances.get(name="web").plugin("sandbox").route()
        """

        async def resolve() -> ResolvedInstance:
            target = await self._next()
            held: object = (await self._locate()).value
            value = self._value
            if (
                held is None
                and value is not None
                and value.done()
                and not value.cancelled()
                and value.exception() is None
            ):
                held = value.result()
            uuid = target.ref.uuid
            if uuid is None:
                known = getattr(held, "uuid", None)
                if isinstance(known, str) and known:
                    uuid = known
            return ResolvedInstance(
                target=target,
                uuid=uuid,
                instance=held if isinstance(held, Instance) else None,
            )

        # Addressing a plugin consumes the handle the way chaining does: it is
        # the plugin that will send something, not this handle.
        self._consumed = True
        return self._instances._plugin(name, resolve)

    def sandbox(self, *, plugin: str = PLUGIN_NAME) -> Sandbox:
        """The sandbox plugin on the instance: commands and files inside it.

        ``plugin`` names the plugin when it was attached under another name.

        .. code-block:: python

            sb = ukc.metro("fra").instances.get(uuid=uuid).sandbox()
            result = await sb.exec("uname -a")
        """
        return Sandbox(self.plugin(plugin))


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
        """Delete every match.

        With ``missing_ok``, a match already gone is left out, and a reference
        that matches nothing deletes nothing rather than raising.
        """
        if opts.get("missing_ok") and await self._absent():
            return []
        try:
            deleted = await self._map(lambda handle: handle.delete(**opts))
        except MetroFanoutError as err:
            # The matches already gone are no result of the metros that did delete.
            err.results = [item for item in err.results if item is not None]
            raise
        return [item for item in deleted if item is not None]

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

    def _plugin(self, name: str, resolve: Callable[[], Awaitable[ResolvedInstance]]) -> Plugin:
        """A plugin on the instance a handle resolves to. Used by :class:`InstanceHandle`."""
        return Plugin(
            name,
            resolve=resolve,
            read=lambda target: self.read(target, {}),
            config=self._session.platform,
        )

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
        check_spec(spec, models.CreateInstanceRequest, self.noun)
        # A create that waits for the instance to run, by `timeout_s` or the
        # deprecated `wait_timeout_ms`, holds the connection that long, so the
        # read timeout outlasts it, as it does for `wait()`.
        wait = _create_wait_seconds(spec)
        if wait is not None and "timeout" not in call:
            call["timeout"] = _outlives(self._session.platform.timeout, wait)
        opts = scoped(call, metros)
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
            # A create that waited for the instance to run reports a lapsed wait
            # the way `wait` does; an instance that stopped, whatever the
            # message says, is a failed item read for its stop below.
            if wait is not None and _first_state(res) not in ("stopped", "deleted"):
                _timed_out(res, "running")
            try:
                instance = first_tagged(res, _KEY, endpoint.metro, Instance, "instance")
            except UnikraftCloudError as err:
                stopped = await self._stopped(err, endpoint, opts)
                if stopped is None:
                    raise
                raise stopped from err
            target = MetroTarget(
                metro=endpoint.metro, base_url=endpoint.base_url, ref=_ref_of(instance)
            )
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
                lookup=True,
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
        timeout_seconds: int | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[DeletedInstance]:
        """Delete one or more instances.

        An instance the API could not delete raises, with the ones it did on the
        error's ``results``. ``timeout_seconds`` blocks until they are gone, or
        for that long; ``-1`` waits for as long as the platform allows. The read
        timeout is stretched to outlast the wait only when no ``timeout`` was given.

        References are located first when the scope spans metros, so each
        instance is deleted only in the metro that holds it.
        """
        opts = scoped(options(headers, base_url, timeout), metros)
        if timeout_seconds is not None and "timeout" not in opts:
            opts["timeout"] = _outlives(self._session.platform.timeout, timeout_seconds)
        extra = {} if timeout_seconds is None else {"timeout_s": timeout_seconds}

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [
                models.DeleteInstanceRequestItem.model_validate(ref_dict(ref) | extra)
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

    async def _stopped(
        self, err: UnikraftCloudError, endpoint: MetroEndpoint, opts: ScopeOptions
    ) -> InstanceStoppedError | None:
        """The failed create as a stopped instance, when that is what it was.

        The API reports an instance that stopped before it was running as a
        failed item naming the instance and its state, with no error code of
        its own, so the instance is read for the reason; one deleted on stop
        is reported in the ``deleted`` state, and what the item says is all
        there is. An item in another state, or one carrying the API's own
        error code -- a name already taken, say -- is that failure, and stays
        as it is.
        """
        item = next((error for error in err.errors or () if error.uuid), None)
        if item is None or item.uuid is None:
            return None
        if item.state is not None and item.state not in ("stopped", "deleted"):
            return None
        if item.state is None and item.code is not None:
            return None
        uuid = item.uuid
        instance: Instance | None = None
        if item.state != "deleted":
            target = MetroTarget(
                metro=endpoint.metro, base_url=endpoint.base_url, ref=Ref(uuid=uuid)
            )
            try:
                instance = await self.read(target, opts)
            except NotFoundError as missing:
                # A route that is not there fails the read like any other failure.
                if not missing.absent:
                    return None
                # Gone between the create's answer and the read.
                instance = None
            except UnikraftCloudError:
                return None
            if instance is not None and instance.state not in ("stopped", "deleted"):
                return None
        gone = instance is None or instance.state == "deleted"
        if instance is None:
            # What the failed item said is all there is.
            instance = Instance(
                uuid=uuid, name=item.name, state=item.state or "stopped", metro=endpoint.metro
            )
        detail = instance.describe_stop()
        return InstanceStoppedError(
            f"instance {describe_ref(_ref_of(instance))} stopped before it was running"
            + (f": {detail}" if detail else "")
            + ("; it is gone already" if gone else ""),
            instance=instance,
            errors=err.errors,
            body=err.body,
        )

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
