# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The base every idiomatic ("porcelain") resource client is built on. It owns the
# metro scope, the generated plumbing client the operations are issued through,
# and the two hard problems of a metro-scoped API: finding which metro holds a
# named resource, and grouping a bulk operation by metro.

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from .errors import NotFoundError
from .fanout import AmbiguousRefError, MetroFailure, MetroFanoutError, fanout_settled
from .handle import Located, MetroTarget
from .http import ApiClient, CallOptions
from .metro import Metro, MetroEndpoint, MetroScope, metro_endpoint, with_metro
from .response import Ref, describe_ref, envelope_entries, require_first
from .session import Session

__all__ = [
    "MetroGroup",
    "Resource",
    "ScopeOptions",
    "first_tagged",
    "list_tagged",
]

A = TypeVar("A", bound=ApiClient)
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")


class ScopeOptions(CallOptions, total=False):
    """Call options plus a per-call override of which metros to cover."""

    #: Metros this call covers, overriding the client's scope: ``"all"``, one
    #: metro, or a list. Naming metros also skips metro discovery.
    metros: MetroScope | None


@dataclass(frozen=True)
class MetroGroup:
    """A bulk operation's references, grouped by the metro that holds them."""

    endpoint: MetroEndpoint
    refs: list[Ref]


def first_tagged(envelope: BaseModel, key: str, metro: Metro, cls: type[T], what: str) -> T:
    """Unwrap the single resource an operation reports and tag it with its metro."""
    return with_metro(require_first(envelope_entries(envelope, key), what), metro, cls)


def list_tagged(envelope: BaseModel, key: str, metro: Metro, cls: type[T]) -> list[T]:
    """Unwrap a list response and tag every entry with the metro that served it."""
    return [with_metro(entry, metro, cls) for entry in envelope_entries(envelope, key)]


class Resource(Generic[A]):
    """Base class for the idiomatic resource clients.

    Each *holds* -- rather than extends -- its generated plumbing client, keeping
    the two layers distinct: short verbs here, raw spec operations on
    :attr:`Resource.api`.
    """

    #: Human-readable noun used in error messages, e.g. ``"instance"``.
    noun: str = "resource"

    def __init__(self, session: Session, scope: MetroScope, api: A) -> None:
        #: The raw ("plumbing") client for this resource: every operation in the
        #: OpenAPI specification, returning the response envelope untouched.
        #: Calls go to the client's default metro unless given a ``base_url``.
        self.api = api
        self._session = session
        self._scope = scope

    async def _endpoints(self, opts: ScopeOptions) -> list[MetroEndpoint]:
        """The endpoints a call covers, honouring a per-call scope or base URL."""
        # An explicit per-call base URL names exactly one endpoint, whatever the
        # scope says; it is how callers already redirect a single call.
        base_url = opts.get("base_url")
        if base_url is not None:
            return [MetroEndpoint(metro=base_url, base_url=base_url)]
        return await self._session.resolve(opts.get("metros") or self._scope)

    async def _one_endpoint(self, operation: str, opts: ScopeOptions) -> MetroEndpoint:
        """The single endpoint an operation that must pick one metro should use."""
        base_url = opts.get("base_url")
        if base_url is not None:
            return MetroEndpoint(metro=base_url, base_url=base_url)
        return await self._session.resolve_one(opts.get("metros") or self._scope, operation)

    async def _endpoints_for(self, ref: Ref, opts: ScopeOptions) -> list[MetroEndpoint]:
        """The endpoints to search for one reference.

        A reference that names its own metro needs no search and no discovery.
        """
        if ref.metro is not None and opts.get("base_url") is None:
            # An explicitly configured endpoint still wins: there is only one to
            # talk to.
            return [self._session.pinned or metro_endpoint(ref.metro)]
        return await self._endpoints(opts)

    async def _locate(
        self,
        ref: Ref,
        opts: ScopeOptions,
        find: Callable[[MetroEndpoint], Awaitable[T | None]],
    ) -> Located[T]:
        """Find which metro holds a single resource.

        Nothing is sent when the answer is already known -- a reference carrying
        its metro, or a scope of exactly one -- which is what keeps
        ``get(name=...).suspend()`` down to one request. Otherwise every metro in
        scope is asked concurrently, and the resource that was found travels back
        with the target so it need not be read again.

        A name can exist in several metros at once. When it does, this raises
        :class:`AmbiguousRefError` carrying every match rather than picking one,
        because the caller may be about to mutate it.
        """
        endpoints = await self._endpoints_for(ref, opts)
        if len(endpoints) == 1:
            return Located(target=_target(endpoints[0], ref))

        found = await self._search(ref, endpoints, find)
        if len(found) > 1:
            metros = [endpoint.metro for endpoint, _ in found]
            identifier = "uuid" if ref.uuid is not None else "name"
            value = ref.uuid if ref.uuid is not None else ref.name
            raise AmbiguousRefError(
                f"{self.noun} {describe_ref(ref)} exists in {len(found)} metros "
                f"({', '.join(metros)}). Say which one with "
                f'`{identifier}="{value}", metro="{metros[0]}"`, '
                f"or act on all of them with `each()`.",
                [match for _, match in found],
            )

        endpoint, value_found = found[0]
        return Located(target=_target(endpoint, ref), value=value_found)

    async def _locate_all(
        self,
        ref: Ref,
        opts: ScopeOptions,
        find: Callable[[MetroEndpoint], Awaitable[T | None]],
    ) -> list[Located[T]]:
        """Locate *every* metro holding a resource matching the reference.

        The same name in five metros is five results, not an error.
        """
        endpoints = await self._endpoints_for(ref, opts)
        if len(endpoints) == 1:
            # One endpoint: the reference is already unambiguous, so read it
            # lazily like `_locate()` does rather than spending a request to
            # confirm it exists.
            return [Located(target=_target(endpoints[0], ref))]

        found = await self._search(ref, endpoints, find)
        return [Located(target=_target(endpoint, ref), value=value) for endpoint, value in found]

    async def _search(
        self,
        ref: Ref,
        endpoints: Sequence[MetroEndpoint],
        find: Callable[[MetroEndpoint], Awaitable[T | None]],
    ) -> list[tuple[MetroEndpoint, T]]:
        """Ask every endpoint for the reference concurrently and return the matches.

        Absent is not a failure -- most metros legitimately do not hold it -- but
        finding nothing anywhere is, as is finding nothing while some metro was
        unreachable.
        """
        outcomes = await fanout_settled(endpoints, find)
        failures: list[MetroFailure] = []
        found: list[tuple[MetroEndpoint, T]] = []
        for outcome in outcomes:
            if not outcome.ok:
                failures.append(MetroFailure(metro=outcome.endpoint.metro, error=outcome.error))
            elif outcome.value is not None:
                found.append((outcome.endpoint, outcome.value))

        if not found:
            searched = ", ".join(endpoint.metro for endpoint in endpoints)
            # A metro that failed might have been the one holding it, so say so
            # rather than reporting a bare 404 the caller cannot act on.
            if failures:
                unreachable = ", ".join(failure.metro for failure in failures)
                raise MetroFanoutError(
                    f"{self.noun} {describe_ref(ref)} was not found in {searched}, and "
                    f"{len(failures)} of those metros could not be reached: {unreachable}.",
                    failures,
                )
            raise NotFoundError(
                f"{self.noun} {describe_ref(ref)} not found in {searched}",
                kind="http",
                status=404,
            )
        return found

    async def _group_by_metro(
        self,
        refs: Sequence[Ref],
        opts: ScopeOptions,
        find: Callable[[MetroEndpoint, Ref], Awaitable[T | None]],
    ) -> list[MetroGroup]:
        """Group references by the metro that holds them.

        A bulk operation then becomes one call per metro. Free when the scope is a
        single metro or every reference names its own; otherwise they are located
        first.

        A reference matching in several metros contributes to each of them: a bulk
        operation says what it means, and the scope is what bounds it. Narrow the
        scope or qualify the reference to act on one.
        """
        endpoints = await self._endpoints(opts)
        if len(endpoints) == 1 and all(ref.metro is None for ref in refs):
            return [MetroGroup(endpoint=endpoints[0], refs=list(refs))]

        async def locate(ref: Ref) -> list[Located[T]]:
            return await self._locate_all(ref, opts, lambda endpoint: find(endpoint, ref))

        located = await asyncio.gather(*(locate(ref) for ref in refs))

        groups: dict[str, MetroGroup] = {}
        for hit in [item for group in located for item in group]:
            target = hit.target
            group = groups.get(target.base_url)
            if group is None:
                groups[target.base_url] = MetroGroup(
                    endpoint=MetroEndpoint(metro=target.metro, base_url=target.base_url),
                    refs=[target.ref],
                )
            else:
                group.refs.append(target.ref)
        return list(groups.values())

    async def _run_groups(
        self,
        groups: Sequence[MetroGroup],
        each: Callable[[MetroGroup], Awaitable[list[R]]],
    ) -> list[R]:
        """Run one bulk call per metro group concurrently and concatenate the results.

        Metros that answered are reported even when others failed; the aggregate
        :class:`MetroFanoutError` is raised after the successful results are in
        hand, on it as ``err.results``.
        """
        if len(groups) == 1:
            return await each(groups[0])

        by_endpoint = {group.endpoint.base_url: group for group in groups}
        outcomes = await fanout_settled(
            [group.endpoint for group in groups],
            lambda endpoint: each(by_endpoint[endpoint.base_url]),
        )

        results: list[R] = []
        failures: list[MetroFailure] = []
        for outcome in outcomes:
            if outcome.ok:
                results.extend(outcome.value)
            else:
                failures.append(MetroFailure(metro=outcome.endpoint.metro, error=outcome.error))
        if failures:
            metros = ", ".join(failure.metro for failure in failures)
            error = MetroFanoutError(
                f"{len(failures)} of {len(groups)} metros failed: {metros}.",
                failures,
            )
            # The partial results are the useful half of a partial failure; a bulk
            # call cannot yield them like an iteration can, so carry them along.
            error.results = list(results)
            raise error
        return results

    def _call(self, endpoint: MetroEndpoint, opts: ScopeOptions) -> CallOptions:
        """Build the per-call options every plumbing operation accepts."""
        call: CallOptions = {"base_url": endpoint.base_url}
        if "headers" in opts:
            call["headers"] = opts["headers"]
        if "timeout" in opts:
            call["timeout"] = opts["timeout"]
        return call


def _target(endpoint: MetroEndpoint, ref: Ref) -> MetroTarget:
    """Pin a reference to an endpoint, dropping the metro it named.

    The metro said *where* to send the request; from here on the endpoint says
    that, and the API rejects a body carrying an unknown field.
    """
    return MetroTarget(
        metro=endpoint.metro,
        base_url=endpoint.base_url,
        ref=Ref(uuid=ref.uuid, name=ref.name),
    )
