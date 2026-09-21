# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.

from __future__ import annotations

from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Generator,
    Sequence,
)
from types import TracebackType
from typing import Any, TypeVar

from typing_extensions import Self

from .errors import UnikraftCloudError

__all__ = ["DEFAULT_PAGE_SIZE", "TRAIL_LENGTH", "Listing", "collect", "paginate"]

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 100

#: How many recently-read cursors a listing keeps, to resume from an earlier one
#: when the item it was reading from is removed.
TRAIL_LENGTH = 32


async def paginate(
    fetch_page: Callable[[int, str | None], Awaitable[list[T]]],
    cursor: Callable[[T], str | None],
    page_size: int | None = None,
) -> AsyncIterator[T]:
    """Lazily iterate every item across all pages of a list endpoint.

    The platform API paginates with a ``count`` page size and a ``from`` cursor;
    a page shorter than ``count`` marks the end. The cursor is inclusive: a page
    starts with the item it names, which the previous page already yielded.

    ``fetch_page`` is called with the page size and the cursor to start at, and
    ``cursor`` extracts the cursor (typically the UUID) from an item.
    """
    count = page_size if page_size and page_size > 0 else DEFAULT_PAGE_SIZE
    start: str | None = None
    # The cursors read most recently, to fall back on if one of them is removed.
    trail: list[str] = []
    while True:
        # After the first page, ask for one more and drop the repeated item.
        page = await fetch_page(count if start is None else count + 1, start)
        if start is not None and not page:
            # The page the cursor names holds not even the cursor itself: that
            # item is gone, so pick the listing up from an earlier one.
            page, start = await _resume(fetch_page, count, trail, start)
        if start is not None and page and cursor(page[0]) == start:
            page = page[1:]
        for item in page:
            yield item
        if len(page) < count:
            return
        read = [found for found in (cursor(item) for item in page) if found is not None]
        trail = (trail + read)[-TRAIL_LENGTH:]
        following = read[-1] if read else None
        # No usable cursor -> stop, rather than requesting the same page forever.
        if following is None or following == start:
            return
        start = following


async def _resume(
    fetch_page: Callable[[int, str | None], Awaitable[list[T]]],
    count: int,
    trail: Sequence[str],
    gone: str,
) -> tuple[list[T], str]:
    """Read on from the most recent item already read that is still there."""
    for start in reversed([found for found in trail if found != gone]):
        page = await fetch_page(count + 1, start)
        if page:
            return page, start
    raise UnikraftCloudError(
        "This listing lost its place: the items it last read are gone. "
        "Read the listing again to start over.",
        kind="http",
    )


async def collect(items: AsyncIterable[T]) -> list[T]:
    """Collect every item of an async iterable into a list."""
    return [item async for item in items]


class Listing(AsyncIterator[T]):
    """Every item of a listing: iterate it lazily, or await it for a list.

    ``async for`` yields each item as the pages arrive, which is what a large
    listing wants. Awaiting reads the whole listing into memory instead.

    A listing left part-read holds a page of every metro in flight, so close one
    you stop early -- with ``async with``, or :meth:`aclose`.

    .. code-block:: python

        async for inst in ukc.instances.list():
            ...
        every = await ukc.instances.list()

        async with ukc.instances.list() as listing:
            async for inst in listing:
                break
    """

    def __init__(self, items: AsyncIterator[T]) -> None:
        self._items = items
        self._consumed = False

    def __aiter__(self) -> AsyncIterator[T]:
        self._claim()
        return self._items

    async def __anext__(self) -> T:
        return await self._items.__anext__()

    def __await__(self) -> Generator[Any, None, list[T]]:
        self._claim()
        return collect(self._items).__await__()

    async def aclose(self) -> None:
        """Release a listing that was not read to the end.

        The metros still in flight are dropped at once, rather than when the
        garbage collector gets to the listing.
        """
        aclose = getattr(self._items, "aclose", None)
        if aclose is not None:
            await aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    def _claim(self) -> None:
        """Take the one pass a listing has, or say that it is already spent."""
        # Reading it twice would otherwise find the pages exhausted and report
        # an empty account.
        if self._consumed:
            raise RuntimeError(
                "This listing has already been read; call list() again for another pass."
            )
        self._consumed = True
