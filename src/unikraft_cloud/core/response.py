# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
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
    "ALREADY_EXISTS_CODE",
    "NOT_FOUND_CODE",
    "Ref",
    "RefLike",
    "as_ref",
    "describe_ref",
    "matched_entries",
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


#: A reference, the mapping form of one (``{"name": "web"}``), or a bare name.
RefLike = Ref | Mapping[str, str | None] | str


def as_ref(value: RefLike) -> Ref:
    """Normalise a reference given as a :class:`Ref`, a mapping, or a name.

    A bare string is a name, since that is what people type.
    """
    if isinstance(value, Ref):
        return value
    if isinstance(value, str):
        return Ref(name=value)
    unknown = set(value) - {"uuid", "name", "metro"}
    if unknown:
        raise TypeError(
            f"A resource reference takes `uuid`, `name` and `metro`; got {sorted(unknown)}."
        )
    return Ref(uuid=value.get("uuid"), name=value.get("name"), metro=value.get("metro"))


def to_refs(refs: RefLike | Sequence[RefLike]) -> list[Ref]:
    """Normalise one reference or a sequence of them into a list."""
    if isinstance(refs, (Ref, Mapping, str)):
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


#: The per-item code the API reports for a referenced resource that is not there.
NOT_FOUND_CODE = 8

#: The API's error code for a name that is already taken.
ALREADY_EXISTS_CODE = 23


def raise_for_envelope(res: BaseModel, key: str | None = None) -> None:
    """Raise if a 2xx response envelope reported a logical error.

    The transport already raises on HTTP-level failures; this catches API-level
    failures reported inside an otherwise-200 envelope. Most responses use
    ``"success"``/``"error"``, but some (e.g. autoscale) add statuses of their
    own like ``"unconfigured"``, so only ``"error"`` counts as a failure.

    The API reports each failed item inside ``data``, as an entry whose own
    ``status`` is ``"error"``: the envelope stays 200 and says
    ``"partial_success"`` or ``"error"``. Any failed item raises. The class
    follows the items: :class:`NotFoundError` when none of them exist. What did
    succeed is on the raised error's ``results``, and the envelope on ``body``.

    ``key`` names the payload list to inspect; without it, every list is.
    """
    failed, succeeded = _split_items(res, key)
    top = _envelope_errors(res)
    if getattr(res, "status", None) != "error" and not failed and not top:
        return
    errors = tuple(_item_error(entry) for entry in failed) + (top or ())
    envelope = getattr(res, "message", None)
    error = _error_for(errors, _describe_failures(failed, len(succeeded), envelope), res)
    error.results = succeeded
    raise error


def _field(entry: Any, name: str) -> Any:
    """One field of a payload entry, whether it arrived parsed or as a mapping."""
    return entry.get(name) if isinstance(entry, Mapping) else getattr(entry, name, None)


def _split_items(res: BaseModel, key: str | None) -> tuple[list[Any], list[Any]]:
    """Split the payload's entries into the failed ones and the rest."""
    data = getattr(res, "data", None)
    if data is None:
        return [], []
    if key is not None:
        lists = [getattr(data, key, None) or []]
    else:
        lists = [v for v in vars(data).values() if isinstance(v, list)]
    failed: list[Any] = []
    succeeded: list[Any] = []
    for entries in lists:
        for entry in entries:
            if _field(entry, "status") == "error":
                failed.append(entry)
            else:
                succeeded.append(entry)
    return failed, succeeded


#: The HTTP status that says the same as an API error code, for the codes that
#: have one. It picks the error class and answers `err.status`.
_STATUS_FOR_CODE = {NOT_FOUND_CODE: 404, ALREADY_EXISTS_CODE: 409}


def _item_error(entry: Any) -> ResponseError:
    """Describe one failed item as an error entry."""
    code = _field(entry, "error")
    code = code if isinstance(code, int) else None
    message = _field(entry, "message")
    uuid = _field(entry, "uuid")
    name = _field(entry, "name")
    return ResponseError(
        status=None if code is None else _STATUS_FOR_CODE.get(code),
        message=message if isinstance(message, str) else None,
        code=code,
        uuid=uuid if isinstance(uuid, str) else None,
        name=name if isinstance(name, str) else None,
    )


def _describe_failures(failed: Sequence[Any], succeeded: int, envelope: str | None) -> str:
    """Say what failed, preferring the items' own messages to the envelope's."""
    messages = (_field(entry, "message") for entry in failed)
    details: list[str] = [m for m in dict.fromkeys(messages) if isinstance(m, str) and m]
    if not details:
        return envelope or "Unikraft Cloud API reported an error"
    if len(failed) == 1 and not succeeded:
        return details[0]
    return f"{len(failed)} of {len(failed) + succeeded} items failed: {'; '.join(details)}"


def _error_for(
    errors: tuple[ResponseError, ...], message: str, res: BaseModel
) -> UnikraftCloudError:
    """Pick the most specific error class every failure agrees on."""
    statuses = {error.status for error in errors}
    status = next(iter(statuses)) if len(statuses) == 1 else None
    if status is None:
        return UnikraftCloudError(message, kind="http", errors=errors or None, body=res)
    return error_for_status(status, message, errors=errors, body=res)


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


def matched_entries(res: BaseModel, key: str) -> list[Any]:
    """The entries a lookup for several references found, ignoring the misses.

    Asking one metro about several references reports the ones it does not hold
    as not-found items beside the ones it does. Those are absences rather than
    failures; any other failed item still raises.
    """
    try:
        return envelope_entries(res, key)
    except UnikraftCloudError as err:
        if err.errors and all(e.code == NOT_FOUND_CODE for e in err.errors):
            return list(err.results)
        raise


def envelope_entries(res: BaseModel, key: str) -> list[Any]:
    """Read one of the envelope payload's lists, after checking for an error.

    Returns an empty list when the payload or the list is absent, which is how
    the API reports "nothing matched".
    """
    raise_for_envelope(res, key)
    data = getattr(res, "data", None)
    if data is None:
        return []
    entries = getattr(data, key, None)
    return list(entries) if entries else []
