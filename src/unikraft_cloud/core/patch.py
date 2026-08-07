# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Updating a resource. The API models an update as a list of
# `{prop, op, value}` triples with an untyped `value` -- precise on the wire,
# clunky to write and unchecked by any tool. This turns that into two idiomatic
# forms:
#
#     update(memory_mb=512)                              # ops inferred
#     edit().set(...).add(...).delete(...).apply()       # ops stated outright
#
# Both compile down to the same triples, sent in one request.

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from typing_extensions import Self

__all__ = [
    "REMOVE",
    "PatchItem",
    "PatchOp",
    "Remove",
    "ResourceEditor",
    "to_patch_items",
]

R = TypeVar("R")

#: The operations every mutable property supports.
PatchOp = Literal["set", "add", "del"]


class Remove:
    """The value that means "remove this property altogether".

    JavaScript spells this ``null``, following JSON Merge Patch where a null
    erases rather than assigns. Python cannot: ``None`` is how a caller spells
    "no opinion", and an update takes its properties as keyword arguments, so
    omitting one and clearing one have to look different.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "REMOVE"


#: Pass as a property's value to remove the property.
#:
#: .. code-block:: python
#:
#:     await ukc.instances.get(name="web").update(autokill=REMOVE)
REMOVE = Remove()


@dataclass(frozen=True)
class PatchItem:
    """One ``{prop, op, value}`` triple, as the API models an update."""

    prop: str
    op: PatchOp
    value: Any = None


def to_patch_items(
    patch: Mapping[str, Any],
    op: PatchOp,
    normalise: Callable[[str, Any], Any] | None = None,
) -> list[PatchItem]:
    """Turn a mapping of property changes into wire triples.

    ``None`` values are skipped, so spreading optional values into an update is
    safe. :data:`REMOVE` always means "remove this property", whichever method
    supplied it.
    """
    items: list[PatchItem] = []
    for prop, value in patch.items():
        if value is None:
            continue
        if isinstance(value, Remove):
            # A bare `del` carries no value: the whole property goes.
            items.append(PatchItem(prop=prop, op="del"))
            continue
        items.append(
            PatchItem(prop=prop, op=op, value=normalise(prop, value) if normalise else value)
        )
    return items


class ResourceEditor(Generic[R]):
    """A staged edit: chain the operations, then ``apply()`` to send them as one.

    Each call appends, so the order you write is the order the API receives.

    .. code-block:: python

        await (
            ukc.instances.get(name="web")
            .edit()
            .set(memory_mb=512)
            .add(env={"LOG_LEVEL": "debug"})
            .delete(tags=["staging"])
            .apply()
        )
    """

    def __init__(
        self,
        commit: Callable[[list[PatchItem]], R],
        what: str,
        normalise: Callable[[str, Any], Any] | None = None,
    ) -> None:
        self._items: list[PatchItem] = []
        self._commit = commit
        self._what = what
        self._normalise = normalise

    def set(self, **patch: Any) -> Self:
        """Replace these properties' values. :data:`REMOVE` removes one instead."""
        self._items.extend(to_patch_items(patch, "set", self._normalise))
        return self

    def add(self, **patch: Any) -> Self:
        """Merge into these properties, keeping what is already there."""
        self._items.extend(to_patch_items(patch, "add", self._normalise))
        return self

    def delete(self, **patch: Any) -> Self:
        """Remove members from these properties, or the whole property with :data:`REMOVE`.

        Named ``delete`` rather than ``del``, which is a Python keyword.
        """
        self._items.extend(to_patch_items(patch, "del", self._normalise))
        return self

    @property
    def changes(self) -> list[PatchItem]:
        """The wire triples staged so far."""
        return list(self._items)

    def apply(self) -> R:
        """Send every staged change as one update."""
        if not self._items:
            raise TypeError(
                f"This {self._what} edit has no changes to apply; "
                f"call set(), add() or delete() first."
            )
        return self._commit(self._items)
