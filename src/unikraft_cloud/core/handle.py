# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
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
from collections.abc import Awaitable, Callable, Generator
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from .metro import Metro, MetroEndpoint
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
    #: Whether a chained operation has to await this handle's own value first.
    #: True for handles that represent an operation (`suspend()` must complete
    #: before a chained `wait()` runs); false for a handle that merely identifies
    #: a resource, which is what keeps `get(ref).suspend()` down to one request.
    sequential: bool = False


class ResourceHandle(Generic[T]):
    """A lazily-evaluated reference to one resource in one metro.

    Nothing is sent until the handle is awaited or a chained operation runs, and
    each step is performed at most once however many times it is awaited.
    """

    def __init__(self, steps: HandleSteps[T]) -> None:
        self._steps = steps
        self._located: asyncio.Future[Located[T]] | None = None
        self._value: asyncio.Future[T] | None = None
        self._consumed = False

    def __await__(self) -> Generator[Any, None, T]:
        # Being awaitable is the point: it lets `await ukc.instances.get(ref)`
        # return the instance while `ukc.instances.get(ref).suspend()` keeps
        # chaining.
        self._consumed = True
        return self._evaluate().__await__()

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
    ) -> HandleSteps[R]:
        """Steps for an operation chained onto this handle.

        The operation runs against the metro this handle resolved to, after this
        handle's own operation has completed. Chaining consumes this handle, so
        only the end of a chain can warn about never being awaited.
        """
        self._consumed = True

        async def locate() -> Located[R]:
            return Located(target=await self._next())

        return HandleSteps(locate=locate, fetch=fetch, what=self._steps.what, sequential=True)

    async def _next(self) -> MetroTarget:
        """The target a chained operation should act on, performing this step first."""
        if self._steps.sequential:
            await self._evaluate()
        return (await self._locate()).target

    def _locate(self) -> Awaitable[Located[T]]:
        if self._located is None:
            # Memoised as a task rather than a coroutine so several awaits, and
            # several chained operations, share the one lookup.
            self._located = asyncio.ensure_future(self._steps.locate())
        return self._located

    def _evaluate(self) -> Awaitable[T]:
        if self._value is None:
            self._value = asyncio.ensure_future(self._read())
        return self._value

    async def _read(self) -> T:
        located = await self._locate()
        if located.value is not None:
            return located.value
        return await self._steps.fetch(located.target)
