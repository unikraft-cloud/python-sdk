# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from typing import TypeVar

__all__ = ["DEFAULT_PAGE_SIZE", "collect", "paginate"]

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 100


async def paginate(
    fetch_page: Callable[[int, str | None], Awaitable[list[T]]],
    cursor: Callable[[T], str | None],
    page_size: int | None = None,
) -> AsyncIterator[T]:
    """Lazily iterate every item across all pages of a list endpoint.

    The platform API paginates with a ``count`` page size and a ``from`` cursor;
    a page shorter than ``count`` marks the end.

    ``fetch_page`` is called with the page size and the cursor to start after,
    and ``cursor`` extracts the cursor (typically the UUID) from an item.
    """
    count = page_size if page_size and page_size > 0 else DEFAULT_PAGE_SIZE
    start: str | None = None
    while True:
        page = await fetch_page(count, start)
        for item in page:
            yield item
        if len(page) < count:
            return
        following = cursor(page[-1])
        # No usable cursor -> stop, rather than requesting the same page forever.
        if following is None or following == start:
            return
        start = following


async def collect(items: AsyncIterable[T]) -> list[T]:
    """Collect every item of an async iterable into a list."""
    return [item async for item in items]
