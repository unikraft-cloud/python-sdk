# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The chainable resource handle. Single-resource operations return a handle
# rather than a coroutine, so calls compose:
#
#     await ukc.instances.get(name="web").suspend()
#
# A handle is awaitable in its own right, so awaiting one yields the resource
# itself, exactly as a plain `get()` returning a coroutine would.

from __future__ import annotations

import asyncio
import contextlib
import warnings
from collections.abc import Awaitable, Callable, Generator, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Generic, TypeVar

from .http import UNSET, CallOptions, TimeoutOption, Unset
from .metro import Metro, MetroEndpoint, metro_base_url
from .response import Ref

__all__ = [
    "HandleSteps",
    "Located",
    "MetroTarget",
    "ResourceHandle",
]

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True)
class MetroTarget(MetroEndpoint):
    """A resource pinned to the metro that actually holds it."""

    #: The reference the operation was given, without its metro.
    ref: Ref


@dataclass(frozen=True)
class Located(Generic[T]):
    """The outcome of locating a resource.

    A scope spanning several metros has to ask them to find out which one holds
    the resource, and that answer already contains the resource -- so it is
    carried here instead of being fetched twice.
    """

    target: MetroTarget
    value: T | None = None


@dataclass(frozen=True)
class HandleSteps(Generic[T]):
    """How a handle resolves its target and its value."""

    #: Work out which metro holds the resource (may perform a request).
    locate: Callable[[], Awaitable[Located[T]]]
    #: Produce the handle's value, once located.
    fetch: Callable[[MetroTarget], Awaitable[T]]
    #: What this handle refers to, for the never-awaited warning.
    what: str = "resource"
    #: Whether the resource was already found, which is how a set hands out its
    #: matches. Such a handle holds no unsent work, so dropping it is not a
    #: forgotten `await` and warns about nothing.
    located: bool = False
    #: The call options the handle was made with. Operations chained onto it
    #: start from these, so a header given to `get()` reaches `suspend()` too.
    options: CallOptions = field(default_factory=lambda: CallOptions())
    #: Whether a chained operation has to await this handle's own value first.
    #: True for handles that represent an operation (`suspend()` must complete
    #: before a chained `wait()` runs); false for a handle that merely identifies
    #: a resource, which is what keeps `get(ref).suspend()` down to one request.
    sequential: bool = False
    #: Whether `locate` only reads, so the next await repeats a lookup that
    #: failed. Unset for a create; a chained operation inherits it from its parent.
    lookup: bool = False


class ResourceHandle(Generic[T]):
    """A lazily-evaluated reference to one resource in one metro.

    Nothing is sent until the handle is awaited or a chained operation runs.
    However many times it is awaited, an operation is performed once, and a
    lookup once unless it failed, in which case the next await repeats it.
    """

    def __init__(self, steps: HandleSteps[T]) -> None:
        self._steps = steps
        self._located: asyncio.Future[Located[T]] | None = None
        self._value: asyncio.Future[T] | None = None
        self._consumed = steps.located

    def __await__(self) -> Generator[Any, None, T]:
        # Being awaitable is the point: it lets `await ukc.instances.get(ref)`
        # return the instance while `ukc.instances.get(ref).suspend()` keeps
        # chaining.
        self._consumed = True
        return self._evaluate().__await__()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} for {self._steps.what}>"

    def __del__(self) -> None:
        # A dropped handle sent nothing. Unlike a dropped coroutine, nothing in
        # the language notices, so say so here: a forgotten `await` is otherwise
        # a silent no-op.
        if not self._consumed:
            # Suppressed because this can run during interpreter shutdown, when
            # the warnings machinery may already be gone.
            with contextlib.suppress(Exception):  # pragma: no cover
                what = self._steps.what
                warnings.warn(
                    f"The handle for {what} was never awaited; no request was sent.",
                    RuntimeWarning,
                    stacklevel=2,
                )

    async def resolve(self) -> MetroTarget:
        """The resource's reference and the metro serving it, resolving the scope."""
        self._consumed = True
        return (await self._locate()).target

    async def where(self) -> Metro:
        """Which metro holds this resource."""
        return (await self.resolve()).metro

    def _chained(
        self,
        fetch: Callable[[MetroTarget], Awaitable[R]],
        opts: CallOptions,
    ) -> HandleSteps[R]:
        """Steps for an operation chained onto this handle.

        The operation runs against the metro this handle resolved to, after this
        handle's own operation has completed. Chaining consumes this handle, so
        only the end of a chain can warn about never being awaited.
        """
        self._consumed = True

        async def locate() -> Located[R]:
            return Located(target=_explicit_target(await self._next(), opts))

        return HandleSteps(
            locate=locate,
            fetch=fetch,
            what=self._steps.what,
            sequential=True,
            options=self._steps.options,
            lookup=self._steps.lookup,
        )

    def _options(
        self,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> CallOptions:
        """A chained operation's call options: its own, over the handle's."""
        opts = CallOptions(**self._steps.options)
        if headers is not None:
            opts["headers"] = {**(opts.get("headers") or {}), **headers}
        if base_url is not None:
            opts["base_url"] = metro_base_url(base_url)
        if not isinstance(timeout, Unset):
            opts["timeout"] = timeout
        return opts

    async def _next(self) -> MetroTarget:
        """The target a chained operation should act on, performing this step first."""
        if self._steps.sequential:
            await self._evaluate()
        return (await self._locate()).target

    def _locate(self) -> Awaitable[Located[T]]:
        if self._located is None or (self._steps.lookup and spent(self._located)):
            # Memoised as a task rather than a coroutine so several awaits, and
            # several chained operations, share the one lookup.
            self._located = asyncio.ensure_future(self._steps.locate())
        # Shielded: the task is shared, so one caller giving up on it must not
        # cancel the lookup every other caller is waiting on.
        return asyncio.shield(self._located)

    async def _evaluate(self) -> T:
        located = await self._locate()
        if located.value is not None:
            return located.value
        # Memoised apart from the lookup, so a chained operation's one outcome
        # stands while its parent's lookup is repeated. A handle that only
        # looks a resource up fetches it by a read, made again if it failed.
        retried = self._steps.lookup and not self._steps.sequential
        if self._value is None or (retried and spent(self._value)):
            self._value = asyncio.ensure_future(self._steps.fetch(located.target))
        return await asyncio.shield(self._value)


def spent(task: asyncio.Future[Any] | None) -> bool:
    """Whether a memoised task cannot serve another caller.

    One that failed or was cancelled is not an answer, and one made on another
    event loop cannot be awaited on this one; either is made afresh.
    """
    if task is None:
        return True
    if task.get_loop() is not asyncio.get_running_loop():
        return True
    return task.done() and (task.cancelled() or task.exception() is not None)


def _explicit_target(target: MetroTarget, opts: CallOptions) -> MetroTarget:
    """Where an operation acts: a caller's own base URL wins over the located metro.

    The request goes there, so that is also the metro the result is tagged with
    and the one a reference to another resource is checked against.
    """
    base_url = opts.get("base_url")
    if base_url is None or base_url == target.base_url:
        return target
    return replace(target, metro=base_url, base_url=base_url)
