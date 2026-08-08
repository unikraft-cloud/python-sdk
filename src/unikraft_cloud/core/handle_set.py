# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Acting on every metro that holds a name. Names are unique within a metro, not
# across them, so one name can legitimately refer to a resource in every metro --
# the same service deployed everywhere. `each(name=...)` addresses all of them at
# once, deliberately, instead of forcing a choice between guessing and failing.

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Generator
from typing import Any, Generic, TypeVar

from .fanout import MetroFailure, MetroFanoutError
from .handle import ResourceHandle
from .metro import Metro

__all__ = ["HandleSet"]

T = TypeVar("T")
R = TypeVar("R")
H = TypeVar("H", bound=ResourceHandle[Any])


class HandleSet(Generic[H, T]):
    """Every resource matching one reference, one per metro.

    Awaiting the set yields the resources; calling an operation runs it against
    each metro concurrently and returns one result per metro.

    If some metros fail, the successes are still returned on the raised
    :class:`MetroFanoutError` as ``err.results``.

    .. code-block:: python

        web = ukc.instances.each(name="web")
        await web.where()     # ["fra", "dal", "sin"]
        await web.suspend()   # one result per metro, each tagged
    """

    def __init__(self, locate: Callable[[], Awaitable[list[H]]]) -> None:
        self._locate = locate
        self._handles: asyncio.Future[list[H]] | None = None

    def handles(self) -> Awaitable[list[H]]:
        """The individual handles, one per metro holding the resource."""
        if self._handles is None:
            self._handles = asyncio.ensure_future(self._locate())
        return self._handles

    async def where(self) -> list[Metro]:
        """The metros holding a match."""
        handles = await self.handles()
        return [await handle.where() for handle in handles]

    async def size(self) -> int:
        """How many metros hold a match."""
        handles = await self.handles()
        # Counting them is not leaving work undone, so they must not report
        # themselves as dropped un-awaited.
        for handle in handles:
            handle._disarm()
        return len(handles)

    def __await__(self) -> Generator[Any, None, list[T]]:
        # Awaitable on purpose, like ResourceHandle: `await each(...)` reads every
        # match, while `each(...).suspend()` keeps addressing them as a set.
        return self.all().__await__()

    async def all(self) -> list[T]:
        """Read every match."""
        return await self._map(lambda handle: handle)

    async def _map(self, each: Callable[[H], Awaitable[R]]) -> list[R]:
        """Run one operation per metro concurrently, where each match lives.

        Subclasses use this to expose the resource's own operations.
        """
        handles = await self.handles()

        # The result is returned as a list of nought or one so that a metro's
        # success and its failure are both plain values: gather then preserves
        # handle order, and `None` stays a legitimate result rather than a
        # stand-in for failure.
        async def run(handle: H) -> tuple[list[R], MetroFailure | None]:
            # The handles are already located, so asking where each one lives
            # costs nothing and gives a failure the metro to be reported against.
            metro = await handle.where()
            try:
                return [await each(handle)], None
            # One metro failing must not lose the others' results, so it is
            # collected and reported in the aggregate below.
            except Exception as error:
                return [], MetroFailure(metro=metro, error=error)

        outcomes = await asyncio.gather(*(run(handle) for handle in handles))
        results = [value for values, _ in outcomes for value in values]
        failures = [failure for _, failure in outcomes if failure is not None]

        if failures:
            metros = ", ".join(failure.metro for failure in failures)
            aggregate = MetroFanoutError(
                f"{len(failures)} of {len(handles)} metros failed: {metros}.",
                failures,
            )
            # The partial results are the useful half of a partial failure; a set
            # operation cannot yield them like an iteration can, so carry them.
            aggregate.results = list(results)
            raise aggregate
        return results
