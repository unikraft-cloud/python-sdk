# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The small pieces every resource client repeats: collecting per-call options,
# turning a reference into a body item or a query filter, and tagging a result.

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TypeVar, cast

from pydantic import BaseModel

from ..core.handle import Located, MetroTarget
from ..core.http import CallOptions, TimeoutOption, Unset
from ..core.metro import MetroScope, metro_base_url, same_metro
from ..core.resource import ScopeOptions, first_tagged
from ..core.response import Ref, as_ref, describe_ref, to_query, wire_ref

__all__ = [
    "InstanceLike",
    "at_metro",
    "filter_of",
    "filters_for",
    "name_or_uuid",
    "options",
    "ref_dict",
    "resolved",
    "scoped",
    "tag_first",
]

M = TypeVar("M", bound=BaseModel)
V = TypeVar("V")


def options(
    headers: Mapping[str, str] | None,
    base_url: str | None,
    timeout: TimeoutOption,
) -> CallOptions:
    """Collect the per-call options an operation was given."""
    opts: CallOptions = {}
    if headers is not None:
        opts["headers"] = headers
    if base_url is not None:
        # Normalised like the client's own, so one spelling works everywhere.
        opts["base_url"] = metro_base_url(base_url)
    if not isinstance(timeout, Unset):
        opts["timeout"] = timeout
    return opts


def scoped(opts: CallOptions, metros: MetroScope | None) -> ScopeOptions:
    """Add a per-call metro scope to some call options."""
    # Every call option is also a scope option; the cast is what says so, since
    # TypedDicts do not widen on their own.
    result = cast("ScopeOptions", dict(opts))
    if metros is not None:
        result["metros"] = metros
    return result


def at_metro(target: MetroTarget, opts: CallOptions) -> CallOptions:
    """Point per-call options at the metro a handle resolved to.

    A caller's own ``base_url`` still wins: it names where this one call goes.
    """
    return {"base_url": target.base_url, **opts}


def ref_dict(ref: Ref) -> dict[str, str]:
    """A reference as a request-body item, without the metro it named."""
    return wire_ref(ref)


#: How another resource is named when a request refers to one: a bare string is
#: a name, since that is what people type; a reference says which it is.
InstanceLike = str | Ref | Mapping[str, str]


def name_or_uuid(value: InstanceLike, target: MetroTarget) -> dict[str, str]:
    """The ``{name}``/``{uuid}`` pair naming another resource in a request body.

    The body cannot say which metro the named resource is in: the API looks it
    up where the request lands, which is `target`. A reference qualified with a
    different metro would therefore silently name a same-named resource there,
    so it is rejected instead of quietly dropping its qualifier.
    """
    if isinstance(value, str):
        return {"name": value}
    ref = value if isinstance(value, Ref) else as_ref(value)
    if ref.metro is not None and not same_metro(ref.metro, target):
        raise ValueError(
            f"Cannot refer to the resource with {describe_ref(ref)} from a request "
            f"sent to {target.metro}: both have to be in the same metro."
        )
    return ref_dict(ref)


def filter_of(ref: Ref) -> tuple[list[str] | None, list[str] | None]:
    """The ``uuid`` and ``name`` query filters for a reference.

    Exactly one is set: the API validates whichever field it is given, so a name
    sent in the ``uuid`` filter fails outright.
    """
    query = to_query(ref)
    return query.get("uuid"), query.get("name")


def filters_for(refs: Sequence[Ref]) -> tuple[list[str] | None, list[str] | None]:
    """The ``uuid`` and ``name`` query filters covering several references.

    One filtered listing answers for the whole batch, so both filters are sent
    together and each reference travels in whichever one names it.
    """
    uuids = [ref.uuid for ref in refs if ref.uuid is not None]
    names = [ref.name for ref in refs if ref.name is not None]
    return uuids or None, names or None


def tag_first(
    envelope: BaseModel,
    key: str,
    target: MetroTarget,
    cls: type[M],
    noun: str,
) -> M:
    """Unwrap a single-resource response and tag it with the metro it came from."""
    return first_tagged(envelope, key, target.metro, cls, f"{noun} {describe_ref(target.ref)}")


def resolved(hit: Located[V]) -> Callable[[], Awaitable[Located[V]]]:
    """A locate step for a match that has already been found."""

    async def located() -> Located[V]:
        return hit

    return located
