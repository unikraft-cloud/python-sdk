# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

__all__ = [
    "CONTROLPLANE_BASE_URL",
    "DEFAULT_METRO",
    "KNOWN_METROS",
    "Metro",
    "MetroEndpoint",
    "MetroScope",
    "metro_base_url",
    "metro_endpoint",
    "with_metro",
]

#: A Unikraft Cloud metro (region) code, or a full ``http(s)://`` base URL for a
#: self-hosted or staging deployment. Any string is accepted so new metros work
#: without an SDK upgrade; :data:`KNOWN_METROS` enumerates the ones known when
#: this SDK was published.
Metro = str

#: The metros known at the time this SDK was published.
KNOWN_METROS: tuple[Metro, ...] = (
    "fra",  # Frankfurt, DE
    "dal",  # Dallas, TX, USA
    "sin",  # Singapore
    "was",  # Washington, DC, USA
    "sfo",  # San Francisco, CA, USA
)

#: The metro used when none is configured.
DEFAULT_METRO: Metro = "fra"

#: Which metros an operation covers: every metro the account can reach
#: (``"all"``), a single metro, or an explicit list.
#:
#: .. code-block:: python
#:
#:     ukc.instances.list()                        # the client's default scope
#:     ukc.instances.list(metros="all")            # fan out across every metro
#:     ukc.instances.list(metros=["fra", "dal"])
MetroScope = Metro | Sequence[Metro]

#: The control-plane API base URL. Unlike the platform API, the control plane is
#: global (not metro-scoped).
CONTROLPLANE_BASE_URL = "https://controlplane.unikraft.cloud"

_URL_SCHEME = re.compile(r"^https?://", re.IGNORECASE)


@dataclass(frozen=True)
class MetroEndpoint:
    """A metro paired with the platform API base URL that serves it."""

    #: Metro code (e.g. ``"fra"``), or the base URL itself for an explicit endpoint.
    metro: Metro
    #: Fully-qualified platform API base URL for this metro.
    base_url: str


def metro_base_url(metro: Metro) -> str:
    """Build the API base URL for a metro, e.g. ``fra`` -> ``https://api.fra.unikraft.cloud``.

    A value that is already an ``http(s)://`` URL is used verbatim (minus any
    trailing slash), so ``UKC_METRO`` can point at a staging or self-hosted
    deployment. Generated operation paths already carry the ``/v1`` prefix, so a
    trailing ``/v1`` is dropped rather than duplicated into ``/v1/v1/...``.

    .. code-block:: python

        metro_base_url("fra")  # "https://api.fra.unikraft.cloud"
        metro_base_url("https://api.staging.example.com/v1")
        # "https://api.staging.example.com"
    """
    if _URL_SCHEME.match(metro):
        return re.sub(r"/v1$", "", metro.rstrip("/"))
    return f"https://api.{metro}.unikraft.cloud"


def metro_endpoint(metro: Metro) -> MetroEndpoint:
    """Pair a metro with its base URL."""
    return MetroEndpoint(metro=metro, base_url=metro_base_url(metro))


def is_url(value: str) -> bool:
    """Whether a metro-ish string is already a fully-qualified base URL."""
    return _URL_SCHEME.match(value) is not None


TaggedT = TypeVar("TaggedT", bound=BaseModel)


def with_metro(value: BaseModel, metro: Metro, cls: type[TaggedT]) -> TaggedT:
    """Re-badge a generated model as its metro-tagged subclass.

    The generated models mirror the wire format and know nothing about metros,
    but every result the resource clients hand back says where it came from.
    ``cls`` is the hand-written subclass that adds ``metro``.

    Construction deliberately skips validation: `value` was validated when it was
    parsed, and re-running it on every result of a fan-out would cost real time
    on large listings.
    """
    fields: dict[str, Any] = {name: getattr(value, name) for name in type(value).model_fields}
    tagged = cls.model_construct(
        _fields_set=value.model_fields_set | {"metro"},
        metro=metro,
        **fields,
    )
    # Fields the server sent that the specification does not describe are kept
    # rather than dropped, so a tagged result is never lossier than the raw one.
    extra = value.model_extra
    if extra and tagged.__pydantic_extra__ is not None:
        tagged.__pydantic_extra__.update(extra)
    return tagged
