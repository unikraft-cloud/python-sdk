# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Referring to a resource, and reading the response envelope it comes back in.

from __future__ import annotations

from collections.abc import Awaitable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

from .errors import (
    NotFoundError,
    ResponseError,
    UnikraftCloudError,
    error_for_status,
)
from .metro import Metro

__all__ = [
    "Ref",
    "RefLike",
    "as_ref",
    "describe_ref",
    "or_absent",
    "raise_for_envelope",
    "require_first",
    "to_query",
    "to_refs",
    "wire_ref",
]

E = TypeVar("E")
T = TypeVar("T")


@dataclass(frozen=True)
class Ref:
    """A resource reference: exactly one of ``uuid`` or ``name``.

    The two are mutually exclusive because the API validates every value it is
    given -- sending a name in the ``uuid`` filter fails with
    ``Invalid uuid '<name>'`` -- so a caller has to say which kind of identifier
    they hold.

    A name is only unique within a metro: the same name can exist in several, or
    in every one. Add ``metro`` to say which you mean, which also saves the SDK a
    lookup. A ``uuid`` identifies one resource wherever it lives, so it never
    needs qualifying.

    .. code-block:: python

        Ref(name="web")
        Ref(name="web", metro="fra")
        Ref(uuid="550e8400-e29b-41d4-a716-446655440000")
    """

    uuid: str | None = None
    name: str | None = None
    metro: Metro | None = None

    def __post_init__(self) -> None:
        if self.uuid is None and self.name is None:
            raise TypeError("A resource reference needs either a `uuid` or a `name`.")
        if self.uuid is not None and self.name is not None:
            raise TypeError("A resource reference takes a `uuid` or a `name`, not both.")


#: A reference, or the mapping form of one: ``{"name": "web"}``.
RefLike = Ref | Mapping[str, str | None]


def as_ref(value: RefLike) -> Ref:
    """Normalise a reference given as either a :class:`Ref` or a mapping."""
    if isinstance(value, Ref):
        return value
    unknown = set(value) - {"uuid", "name", "metro"}
    if unknown:
        raise TypeError(
            f"A resource reference takes `uuid`, `name` and `metro`; got {sorted(unknown)}."
        )
    return Ref(uuid=value.get("uuid"), name=value.get("name"), metro=value.get("metro"))


def to_refs(refs: RefLike | Sequence[RefLike]) -> list[Ref]:
    """Normalise one reference or a sequence of them into a list."""
    if isinstance(refs, (Ref, Mapping)):
        return [as_ref(refs)]
    return [as_ref(ref) for ref in refs]


def wire_ref(ref: Ref) -> dict[str, str]:
    """Strip a reference down to what goes on the wire.

    ``metro`` says *where* to send the request, so it must not travel inside the
    request body -- the API would reject the unknown field.
    """
    if ref.uuid is not None:
        return {"uuid": ref.uuid}
    if ref.name is not None:
        return {"name": ref.name}
    raise TypeError("A resource reference needs either a `uuid` or a `name`.")


def to_query(ref: Ref) -> dict[str, list[str]]:
    """Build the single-key ``uuid`` or ``name`` query filter for a reference."""
    return {key: [value] for key, value in wire_ref(ref).items()}


def describe_ref(ref: Ref) -> str:
    """Describe a reference for use in error messages."""
    identifier = f'uuid "{ref.uuid}"' if ref.uuid is not None else f'name "{ref.name}"'
    return identifier if ref.metro is None else f"{identifier} in {ref.metro}"


def raise_for_envelope(res: BaseModel) -> None:
    """Raise if a 2xx response envelope reported a logical error.

    The transport already raises on HTTP-level failures; this catches API-level
    failures reported inside an otherwise-200 envelope. Most responses use
    ``"success"``/``"error"``, but some (e.g. autoscale) add statuses of their
    own like ``"unconfigured"``, so only ``"error"`` counts as a failure.

    A bulk operation that only partly succeeded (``"partial_success"``) carries
    entries in ``errors`` and so raises too. The whole envelope -- including the
    ``data`` for the parts that did succeed -- is on the raised error's ``body``.
    """
    errors = _envelope_errors(res)
    if getattr(res, "status", None) != "error" and not errors:
        return
    message = getattr(res, "message", None) or "Unikraft Cloud API reported an error"
    status = errors[0].status if errors else None
    if status is None:
        raise UnikraftCloudError(message, kind="http", errors=errors, body=res)
    raise error_for_status(status, message, errors=errors, body=res)


def _envelope_errors(res: BaseModel) -> tuple[ResponseError, ...] | None:
    """Read the envelope's ``errors`` list off the parsed model.

    Read field by field rather than through ``model_dump()``: this runs on every
    response, and dumping a page of listings to inspect two fields is wasteful.
    """
    raw = getattr(res, "errors", None)
    if not raw:
        return None
    errors: list[ResponseError] = []
    for entry in raw:
        status = getattr(entry, "status", None)
        message = getattr(entry, "message", None)
        errors.append(
            ResponseError(
                status=status if isinstance(status, int) else None,
                message=message if isinstance(message, str) else None,
            )
        )
    return tuple(errors) or None


def require_first(entries: Sequence[E], what: str) -> E:
    """Return the first entry of a list, or raise a descriptive not-found error.

    Most single-resource operations return the resource inside a singleton list.
    """
    if not entries:
        raise NotFoundError(f"{what} not found", kind="http", status=404)
    return entries[0]


async def or_absent(work: Awaitable[T]) -> T | None:
    """Resolve to ``None`` when a lookup reports the resource is not there.

    Searching several metros for one resource means most of them will legitimately
    answer "not here"; only a real failure should count as a failure.
    """
    try:
        return await work
    except UnikraftCloudError as err:
        if err.status == 404:
            return None
        raise


def envelope_entries(res: BaseModel, key: str) -> list[Any]:
    """Read one of the envelope payload's lists, after checking for an error.

    Returns an empty list when the payload or the list is absent, which is how
    the API reports "nothing matched".
    """
    raise_for_envelope(res)
    data = getattr(res, "data", None)
    if data is None:
        return []
    entries = getattr(data, key, None)
    return list(entries) if entries else []
