# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The base every idiomatic ("porcelain") resource client is built on. It owns the
# metro scope, the generated plumbing client the operations are issued through,
# and the two hard problems of a metro-scoped API: finding which metro holds a
# named resource, and grouping a bulk operation by metro.

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .errors import NotFoundError, UnikraftCloudError
from .fanout import (
    AmbiguousRefError,
    MetroFailure,
    MetroFanoutError,
    fanout_collect,
    fanout_error,
    fanout_settled,
)
from .handle import Located, MetroTarget
from .http import ApiClient, CallOptions
from .metro import Metro, MetroEndpoint, MetroScope, with_metro
from .response import Ref, RefLike, describe_ref, envelope_entries, require_first, to_refs
from .session import Session

__all__ = [
    "MetroGroup",
    "Resource",
    "ScopeOptions",
    "check_spec",
    "first_tagged",
    "list_tagged",
    "refs_matching",
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


def refs_matching(refs: Sequence[Ref], entries: Sequence[Any]) -> list[Ref]:
    """The references a metro's filtered listing accounted for.

    One request asks about every reference at once, so the answer has to be
    paired back up: an entry stands for the reference naming the same resource.
    """
    by_uuid = {entry.uuid: entry for entry in entries if getattr(entry, "uuid", None)}
    by_name = {entry.name: entry for entry in entries if getattr(entry, "name", None)}
    return [
        ref
        for ref in refs
        if (ref.uuid is not None and ref.uuid in by_uuid)
        or (ref.name is not None and ref.name in by_name)
    ]


def _same_ref(one: Ref, other: Ref) -> bool:
    """Whether two references name the same resource."""
    return one.uuid == other.uuid if one.uuid is not None else one.name == other.name


def first_tagged(envelope: BaseModel, key: str, metro: Metro, cls: type[T], what: str) -> T:
    """Unwrap the single resource an operation reports and tag it with its metro."""
    return with_metro(require_first(envelope_entries(envelope, key), what), metro, cls)


def list_tagged(envelope: BaseModel, key: str, metro: Metro, cls: type[T]) -> list[T]:
    """Unwrap a list response and tag every entry with the metro that served it.

    When some entries failed, the ones that did not are tagged on the raised error.
    """
    try:
        entries = envelope_entries(envelope, key)
    except UnikraftCloudError as err:
        err.results = [with_metro(entry, metro, cls) for entry in err.results]
        raise
    return [with_metro(entry, metro, cls) for entry in entries]


def check_spec(spec: Mapping[str, Any], model: type[BaseModel], noun: str) -> None:
    """Reject a property this resource cannot be created with, before anything is sent.

    The wire models keep the fields the specification does not describe, so that
    a newer API stays usable; a misspelled keyword argument would ride along
    with them and be dropped by the server without a word.
    """
    allowed = {name for name in model.model_fields}
    allowed |= {field.alias for field in model.model_fields.values() if field.alias}
    unknown = sorted(set(spec) - allowed)
    if unknown:
        raise TypeError(
            f"{unknown[0]!r} is not one of the properties a new {noun} can be given. "
            f"Expected one of: {', '.join(sorted(allowed))}."
        )


class Resource(Generic[A]):
    """Base class for the idiomatic resource clients.

    Each *holds* -- rather than extends -- its generated plumbing client, keeping
    the two layers distinct: short verbs here, raw spec operations on
    :attr:`Resource.api`.
    """

    #: Human-readable noun used in error messages, e.g. ``"instance"``.
    noun: str = "resource"
    #: The payload key this resource's results are reported under.
    key: str = "resources"

    def __init__(self, session: Session, scope: MetroScope, api: A) -> None:
        #: The raw ("plumbing") client for this resource: every operation in the
        #: OpenAPI specification, returning the response envelope untouched.
        #: Calls go to the client's default metro unless given a ``base_url``.
        self.api = api
        self._session = session
        self._scope = scope

    def __repr__(self) -> str:
        return f"<{type(self).__name__} metros={self._scope!r}>"

    @property
    def session(self) -> Session:
        """The session behind this client: credentials, discovery and its cache."""
        return self._session

    def _scope_of(self, opts: ScopeOptions) -> MetroScope:
        """The scope a call covers: its own ``metros`` when given, else the client's.

        Only an absent override falls back. An empty one is passed on as it is,
        because it says "no metros" -- which the session rejects -- rather than
        "whatever the client covers".
        """
        metros = opts.get("metros")
        return self._scope if metros is None else metros

    async def _endpoints(self, opts: ScopeOptions) -> list[MetroEndpoint]:
        """The endpoints a call covers, honouring a per-call scope or base URL."""
        # An explicit per-call base URL names exactly one endpoint, whatever the
        # scope says; it is how callers already redirect a single call.
        base_url = opts.get("base_url")
        if base_url is not None:
            return [_explicit_endpoint(base_url)]
        return await self._session.resolve(self._scope_of(opts))

    async def _one_endpoint(self, operation: str, opts: ScopeOptions) -> MetroEndpoint:
        """The single endpoint an operation that must pick one metro should use."""
        base_url = opts.get("base_url")
        if base_url is not None:
            return _explicit_endpoint(base_url)
        return await self._session.resolve_one(self._scope_of(opts), operation)

    async def _endpoints_for(self, ref: Ref, opts: ScopeOptions) -> list[MetroEndpoint]:
        """The endpoints to search for one reference.

        A reference that names its own metro needs no search and no discovery.
        """
        if ref.metro is not None and opts.get("base_url") is None:
            return [self._session.endpoint_for(ref.metro)]
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

        The same name in five metros is five results, not an error. Every metro
        in scope is asked, a single one included: the set reports how many
        matches there are and where, so each one has to be confirmed.
        """
        endpoints = await self._endpoints_for(ref, opts)
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
        a metro that could not answer is, whatever the others said: it might
        hold the same name, so the matches in hand are not the whole picture.
        Finding nothing anywhere is a plain not-found.
        """
        outcomes = await fanout_settled(endpoints, find)
        failures: list[MetroFailure] = []
        found: list[tuple[MetroEndpoint, T]] = []
        for outcome in outcomes:
            if not outcome.ok:
                failures.append(MetroFailure(metro=outcome.endpoint.metro, error=outcome.error))
            elif outcome.value is not None:
                found.append((outcome.endpoint, outcome.value))

        searched = ", ".join(endpoint.metro for endpoint in endpoints)
        if failures:
            # A metro that failed might hold it too, so say so rather than acting
            # on the matches as if they were unambiguous -- or, when there are
            # none, reporting a bare 404 the caller cannot act on.
            unreachable = ", ".join(failure.metro for failure in failures)
            if found:
                where = ", ".join(endpoint.metro for endpoint, _ in found)
                error = MetroFanoutError(
                    f"{self.noun} {describe_ref(ref)} was found in {where}, but "
                    f"{len(failures)} of the metros searched could not be reached: "
                    f"{unreachable}. It may exist there too.",
                    failures,
                )
            else:
                error = MetroFanoutError(
                    f"{self.noun} {describe_ref(ref)} was not found in {searched}, and "
                    f"{len(failures)} of those metros could not be reached: {unreachable}.",
                    failures,
                )
            # The matches are the useful half of a partial answer, and a lookup
            # cannot yield them as an iteration would, so carry them along.
            error.results = [match for _, match in found]
            raise error

        if not found:
            raise NotFoundError(
                f"{self.noun} {describe_ref(ref)} not found in {searched}",
                kind="http",
                status=404,
            )
        return found

    async def _group_by_metro(self, refs: Sequence[Ref], opts: ScopeOptions) -> list[MetroGroup]:
        """Group references by the metro that holds them.

        A bulk operation then becomes one call per metro. Free when the scope is a
        single metro or every reference names its own; otherwise they are located
        first.

        A reference matching in several metros contributes to each of them: a bulk
        operation says what it means, and the scope is what bounds it. Narrow the
        scope or qualify the reference to act on one.
        """
        # Nothing to act on: no request says that better than one carrying an
        # empty list, whatever the scope.
        if not refs:
            return []
        # A caller's own base URL names where this call goes, so every reference
        # travels in one group whatever metro it named.
        base_url = opts.get("base_url")
        if base_url is not None:
            return [MetroGroup(endpoint=_explicit_endpoint(base_url), refs=list(refs))]
        # Resolving the scope may mean discovering the metros, which references
        # that name their own never need. Only resolve it when one does not.
        if all(ref.metro is None for ref in refs):
            endpoints = await self._endpoints(opts)
            if len(endpoints) == 1:
                return [MetroGroup(endpoint=endpoints[0], refs=list(refs))]

        # A reference naming its metro is already placed; the rest are looked
        # up, and each metro answers about all of them at once.
        targets = [
            _target(self._session.endpoint_for(ref.metro), ref)
            for ref in refs
            if ref.metro is not None
        ]
        unqualified = [ref for ref in refs if ref.metro is None]
        if unqualified:
            found: list[Located[Any]] = await self._locate_many(unqualified, opts)
            targets.extend(hit.target for hit in found)

        groups: dict[str, MetroGroup] = {}
        for target in targets:
            group = groups.get(target.base_url)
            if group is None:
                groups[target.base_url] = MetroGroup(
                    endpoint=MetroEndpoint(metro=target.metro, base_url=target.base_url),
                    refs=[target.ref],
                )
            else:
                group.refs.append(target.ref)
        return list(groups.values())

    async def _locate_many(self, refs: Sequence[Ref], opts: ScopeOptions) -> list[Located[T]]:
        """Find which metros hold each of several references, in one call per metro.

        The references are asked about together: a metro answers for the whole
        batch, so the cost is the number of metros rather than the number of
        references times the number of metros.
        """
        endpoints = await self._endpoints(opts)
        if len(endpoints) == 1:
            # One endpoint: every reference is already unambiguous, so nothing
            # is sent to confirm what there is no choice about.
            return [Located(target=_target(endpoints[0], ref)) for ref in refs]

        outcomes = await fanout_settled(
            endpoints, lambda endpoint: self._match(endpoint, refs, opts)
        )
        failures = [
            MetroFailure(metro=outcome.endpoint.metro, error=outcome.error)
            for outcome in outcomes
            if not outcome.ok
        ]
        if failures:
            # A metro that could not answer might hold some of these too, so
            # acting on a partial picture would act on the wrong set.
            raise fanout_error(len(endpoints), failures)

        found: list[Located[T]] = [
            Located(target=_target(outcome.endpoint, ref))
            for outcome in outcomes
            if outcome.ok
            for ref in outcome.value
        ]
        missing = [ref for ref in refs if not any(_same_ref(ref, hit.target.ref) for hit in found)]
        if missing:
            searched = ", ".join(endpoint.metro for endpoint in endpoints)
            raise NotFoundError(
                f"{self.noun} {describe_ref(missing[0])} not found in {searched}",
                kind="http",
                status=404,
            )
        return found

    async def _match(
        self, endpoint: MetroEndpoint, refs: Sequence[Ref], opts: ScopeOptions
    ) -> list[Ref]:
        """Which of several references one metro holds, asked in one request.

        Each resource client issues its own filtered listing and pairs the
        answer back up with :func:`refs_matching`.
        """
        raise NotImplementedError

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
        return await fanout_collect(
            [group.endpoint for group in groups],
            lambda endpoint: each(by_endpoint[endpoint.base_url]),
        )

    async def _bulk(
        self,
        refs: RefLike | Sequence[RefLike],
        opts: ScopeOptions,
        cls: type[T],
        each: Callable[[MetroGroup], Awaitable[BaseModel]],
    ) -> list[T]:
        """Run a bulk operation once per metro group and tag every result."""
        groups = await self._group_by_metro(to_refs(refs), opts)

        async def run(group: MetroGroup) -> list[T]:
            return list_tagged(await each(group), self.key, group.endpoint.metro, cls)

        return await self._run_groups(groups, run)

    def _call(self, endpoint: MetroEndpoint, opts: ScopeOptions) -> CallOptions:
        """Build the per-call options every plumbing operation accepts.

        A caller's own ``base_url`` wins: it names where this one call goes.
        """
        call: CallOptions = {"base_url": opts.get("base_url") or endpoint.base_url}
        if "headers" in opts:
            call["headers"] = opts["headers"]
        if "timeout" in opts:
            call["timeout"] = opts["timeout"]
        return call


def _explicit_endpoint(base_url: str) -> MetroEndpoint:
    """The single endpoint a caller's own base URL names."""
    return MetroEndpoint(metro=base_url, base_url=base_url)


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
