# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# The small pieces every resource client repeats: collecting per-call options,
# turning a reference into a body item or a query filter, and tagging a result.

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import TypeVar, cast

from pydantic import BaseModel

from ..core.handle import Located, MetroTarget
from ..core.http import CallOptions, TimeoutOption, Unset
from ..core.metro import MetroScope
from ..core.resource import ScopeOptions, first_tagged
from ..core.response import Ref, as_ref, describe_ref

__all__ = [
    "InstanceLike",
    "at_metro",
    "filter_of",
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
        opts["base_url"] = base_url
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
    """Point per-call options at the metro a handle resolved to."""
    return {**opts, "base_url": target.base_url}


def ref_dict(ref: Ref) -> dict[str, str]:
    """A reference as a request-body item, without the metro it named.

    The metro says *where* to send the request, so it must not travel in the
    body -- the API rejects the unknown field.
    """
    return {"uuid": ref.uuid} if ref.uuid is not None else {"name": ref.name or ""}


#: How another resource is named when a request refers to one: a bare string is
#: a name, since that is what people type; a reference says which it is.
InstanceLike = str | Ref | Mapping[str, str]


def name_or_uuid(value: InstanceLike) -> dict[str, str]:
    """The ``{name}``/``{uuid}`` pair naming another resource in a request body."""
    if isinstance(value, str):
        return {"name": value}
    return ref_dict(value if isinstance(value, Ref) else as_ref(value))


def filter_of(ref: Ref) -> tuple[list[str] | None, list[str] | None]:
    """The ``uuid`` and ``name`` query filters for a reference.

    Exactly one is set: the API validates whichever field it is given, so a name
    sent in the ``uuid`` filter fails outright.
    """
    if ref.uuid is not None:
        return [ref.uuid], None
    return None, [ref.name or ""]


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
