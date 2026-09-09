# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Running one operation across several metros and sewing the results back
# together. The platform API is metro-scoped, so an account-wide view means
# asking every metro and merging what comes back.

from __future__ import annotations

import asyncio
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Sequence,
)
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from .errors import UnikraftCloudError
from .metro import Metro, MetroEndpoint

__all__ = [
    "AmbiguousRefError",
    "MetroFailure",
    "MetroFanoutError",
    "MetroFulfilled",
    "MetroOutcome",
    "MetroRejected",
    "fanout",
    "fanout_error",
    "fanout_settled",
]

T = TypeVar("T")


@dataclass(frozen=True)
class MetroFailure:
    """One metro's failure within a multi-metro operation."""

    #: The metro whose request failed.
    metro: Metro
    #: Whatever that metro's request raised.
    error: BaseException


class MetroFanoutError(UnikraftCloudError):
    """Raised when a multi-metro operation could not be completed everywhere.

    The results from the metros that *did* answer have already been delivered --
    an iteration yields them before this is raised -- so a caller can treat the
    failure as partial rather than losing the whole answer. Operations that
    cannot yield as they go attach them to :attr:`results` instead.
    """

    #: Per-metro failures, in the order they occurred.
    failures: tuple[MetroFailure, ...]
    #: Results from the metros that did answer, for operations that could not
    #: hand them over as they arrived.
    results: list[Any]

    def __init__(self, message: str, failures: Sequence[MetroFailure]) -> None:
        # A single underlying failure is worth surfacing as the status, so callers
        # can keep matching on `err.status == 403`.
        statuses = {
            f.error.status if isinstance(f.error, UnikraftCloudError) else None for f in failures
        }
        super().__init__(
            message,
            kind="fanout",
            status=next(iter(statuses)) if len(statuses) == 1 else None,
            body=tuple(failures),
        )
        self.failures = tuple(failures)
        self.results = []
        if failures:
            self.__cause__ = failures[0].error


class AmbiguousRefError(UnikraftCloudError, Generic[T]):
    """Raised when a name matches in several metros and only one can be acted on.

    Names are unique within a metro, not across them -- the same name commonly
    exists in several -- so this is a routine outcome, not a broken state: qualify
    the reference with ``metro``, narrow the scope, or use ``each()`` to act on
    every match.

    The matches are attached, so recovering costs no further requests.
    """

    #: The metros the name was found in.
    metros: tuple[Metro, ...]
    #: The matching resources, each tagged with its metro.
    matches: tuple[T, ...]

    def __init__(self, message: str, matches: Sequence[T]) -> None:
        super().__init__(message, kind="fanout", body=tuple(matches))
        self.matches = tuple(matches)
        self.metros = tuple(getattr(match, "metro", "") for match in matches)


def _describe_failure(failure: MetroFailure) -> str:
    """Describe a failure compactly, e.g. ``sin (503)``."""
    status = failure.error.status if isinstance(failure.error, UnikraftCloudError) else None
    return failure.metro if status is None else f"{failure.metro} ({status})"


def fanout_error(attempted: int, failures: Sequence[MetroFailure]) -> MetroFanoutError:
    """Build the aggregate error for a partly-failed fan-out."""
    detail = ", ".join(_describe_failure(failure) for failure in failures)
    return MetroFanoutError(
        f"{len(failures)} of {attempted} metros failed: {detail}",
        failures,
    )


async def fanout(
    endpoints: Sequence[MetroEndpoint],
    each: Callable[[MetroEndpoint], AsyncIterable[T]],
) -> AsyncIterator[T]:
    """Iterate ``each(endpoint)`` for every endpoint concurrently, merging them.

    Items are yielded as soon as any metro produces one -- so a slow metro never
    holds up a fast one, and the interleaving is arrival order rather than metro
    order.

    Failures do not stop the merge: every healthy metro is drained first, then a
    single :class:`MetroFanoutError` naming the failed metros is raised. Breaking
    out of the loop early cancels the remaining metros and raises nothing.
    """
    # Single metro: no merge bookkeeping, and failures propagate as themselves
    # rather than being wrapped in a fan-out error.
    if len(endpoints) == 1:
        async for item in each(endpoints[0]):
            yield item
        return

    iterators = {index: aiter(each(endpoint)) for index, endpoint in enumerate(endpoints)}
    steps: dict[asyncio.Task[T], int] = {
        asyncio.ensure_future(anext(iterator)): index for index, iterator in iterators.items()
    }

    failures: list[MetroFailure] = []
    try:
        while steps:
            done, _ = await asyncio.wait(steps, return_when=asyncio.FIRST_COMPLETED)
            # Take one step per pass. Any others that finished stay queued and
            # come back from the next `wait` immediately, so nothing is dropped
            # if the consumer stops iterating part-way through.
            task = next(iter(done))
            index = steps.pop(task)
            try:
                item = task.result()
            except StopAsyncIteration:
                continue
            # Whatever one metro raised is that metro's problem; the others
            # keep going and it is reported in the aggregate below.
            except Exception as error:
                failures.append(MetroFailure(metro=endpoints[index].metro, error=error))
                continue

            # Queue this metro's next page before handing the item to the
            # consumer, so every metro stays in flight while the consumer works.
            steps[asyncio.ensure_future(anext(iterators[index]))] = index
            yield item
    finally:
        # An early `break` or raise in the consumer lands here: release the metros
        # still in flight instead of leaving their requests dangling.
        await _release(steps, iterators.values())

    if failures:
        raise fanout_error(len(endpoints), failures)


async def _release(
    steps: dict[asyncio.Task[T], int],
    iterators: Iterable[AsyncIterator[T]],
) -> None:
    """Cancel the in-flight steps and close the iterators behind them."""
    for task in steps:
        task.cancel()
    if steps:
        # Awaiting the cancellations keeps asyncio from reporting the results
        # nobody collected as never-retrieved exceptions.
        await asyncio.gather(*steps, return_exceptions=True)
    for iterator in iterators:
        aclose = getattr(iterator, "aclose", None)
        if aclose is not None:
            await aclose()


@dataclass(frozen=True)
class MetroFulfilled(Generic[T]):
    """One metro's successful outcome from :func:`fanout_settled`."""

    endpoint: MetroEndpoint
    value: T
    ok: Literal[True] = field(default=True)


@dataclass(frozen=True)
class MetroRejected:
    """One metro's failed outcome from :func:`fanout_settled`."""

    endpoint: MetroEndpoint
    error: BaseException
    ok: Literal[False] = field(default=False)


#: One metro's outcome from :func:`fanout_settled`.
MetroOutcome: TypeAlias = "MetroFulfilled[T] | MetroRejected"


async def fanout_settled(
    endpoints: Sequence[MetroEndpoint],
    each: Callable[[MetroEndpoint], Awaitable[T]],
) -> list[MetroOutcome[T]]:
    """Run ``each(endpoint)`` for every endpoint concurrently, reporting every outcome.

    Used by single-resource operations, which cannot yield partial results and so
    need to see the whole picture before deciding what to raise.
    """

    async def settle(endpoint: MetroEndpoint) -> MetroOutcome[T]:
        try:
            return MetroFulfilled(endpoint=endpoint, value=await each(endpoint))
        # Reporting every outcome is the point, so nothing propagates here.
        except Exception as error:
            return MetroRejected(endpoint=endpoint, error=error)

    return list(await asyncio.gather(*(settle(endpoint) for endpoint in endpoints)))
