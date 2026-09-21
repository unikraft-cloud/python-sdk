# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# One error type for every failure of either API, so `except UnikraftCloudError`
# catches the lot however the request went wrong. The status-specific subclasses
# are a convenience on top: they are raised for the statuses they name, so
# `except NotFoundError` and `if err.status == 404` are both valid.

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "AlreadyExistsError",
    "AuthenticationError",
    "ErrorKind",
    "NotFoundError",
    "RateLimitError",
    "ResponseError",
    "ServerError",
    "UnikraftCloudError",
    "UnikraftCloudWarning",
    "WaitTimeoutError",
    "error_for_status",
    "report_warnings",
]

#: The kind of failure an :class:`UnikraftCloudError` represents. ``"fanout"``
#: covers failures that are not a single request's fault: a multi-metro
#: operation where some metros failed, or an ambiguous or unusable metro scope.
ErrorKind = Literal["http", "network", "parse", "fanout"]


@dataclass(frozen=True)
class ResponseError:
    """A single error entry returned within a response envelope."""

    #: The HTTP status code associated with the error.
    status: int | None = None
    #: Optional human-readable detail.
    message: str | None = None
    #: The API's own error code, for an item of a request that failed.
    code: int | None = None
    #: The UUID of the item that failed, when the API names it that way.
    uuid: str | None = None
    #: The name of the item that failed, when the API names it that way.
    name: str | None = None


class UnikraftCloudError(Exception):
    """Raised when a request fails at the transport, HTTP or API level."""

    #: Whether this was an HTTP, network, parse or fan-out failure.
    kind: ErrorKind
    #: HTTP status code, when available.
    status: int | None
    #: Structured errors returned in the response envelope, when available.
    errors: tuple[ResponseError, ...] | None
    #: The parsed response body, when available.
    body: Any
    #: What did succeed when a request only partly failed, e.g. the instances a
    #: bulk delete removed before one of its items failed.
    results: list[Any]

    def __init__(
        self,
        message: str,
        *,
        kind: ErrorKind,
        status: int | None = None,
        errors: tuple[ResponseError, ...] | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.errors = errors
        self.body = body
        self.results = []

    def __reduce__(self) -> tuple[Any, ...]:
        # Pickle rebuilds an exception by calling its class with `args` alone,
        # which misses every keyword-only field. Restore the state instead.
        return (_rebuild_error, (type(self), str(self), self.__dict__.copy()))


def _rebuild_error(
    cls: type[UnikraftCloudError], message: str, state: dict[str, Any]
) -> UnikraftCloudError:
    """Rebuild a pickled error, whatever its subclass takes at construction."""
    error = cls.__new__(cls)
    Exception.__init__(error, message)
    error.__dict__.update(state)
    return error


class AuthenticationError(UnikraftCloudError):
    """The token was missing, invalid, or not permitted to do this (401, 403)."""


class NotFoundError(UnikraftCloudError):
    """The resource does not exist (404)."""


class AlreadyExistsError(UnikraftCloudError):
    """A resource of that name is already there (409)."""


class WaitTimeoutError(UnikraftCloudError, TimeoutError):
    """A wait ended before the resource reached the state it waited for.

    Also a builtin :class:`TimeoutError`, so ``except TimeoutError`` catches it
    beside every other timeout a caller handles.
    """

    #: The state the resource was in when the wait ended, when the API says so.
    state: str | None = None


class RateLimitError(UnikraftCloudError):
    """Too many requests (429)."""


class ServerError(UnikraftCloudError):
    """The API failed to handle an otherwise valid request (5xx)."""


def error_for_status(
    status: int,
    message: str,
    *,
    kind: ErrorKind = "http",
    errors: tuple[ResponseError, ...] | None = None,
    body: Any = None,
) -> UnikraftCloudError:
    """Build the most specific error class that applies to an HTTP status."""
    cls: type[UnikraftCloudError]
    if status in (401, 403):
        cls = AuthenticationError
    elif status == 404:
        cls = NotFoundError
    elif status == 409:
        cls = AlreadyExistsError
    elif status == 429:
        cls = RateLimitError
    elif status >= 500:
        cls = ServerError
    else:
        cls = UnikraftCloudError
    return cls(message, kind=kind, status=status, errors=errors, body=body)


class UnikraftCloudWarning(UserWarning):
    """Something the API reported beside an answer it still gave."""


def report_warnings(body: Any) -> None:
    """Re-raise the warnings a response envelope carries as Python warnings.

    The API reports a deprecated field or a request it had to adjust this way,
    beside the answer itself, so the notice reaches whoever can act on it.
    """
    if not isinstance(body, dict):
        return
    entries = body.get("warnings")
    if not isinstance(entries, list):
        return
    for entry in entries:
        message = entry.get("message") if isinstance(entry, dict) else entry
        if isinstance(message, str) and message:
            warnings.warn(message, UnikraftCloudWarning, stacklevel=2)


def parse_response_errors(body: Any) -> tuple[ResponseError, ...] | None:
    """Read the envelope's ``errors`` list, tolerating anything unexpected.

    The error path cannot assume the body matches the specification -- that
    assumption is often exactly what failed -- so every field is read
    defensively.
    """
    if not isinstance(body, dict):
        return None
    raw = body.get("errors")
    if not isinstance(raw, list) or not raw:
        return None
    errors: list[ResponseError] = []
    for entry in raw:
        if isinstance(entry, dict):
            status = entry.get("status")
            message = entry.get("message")
            errors.append(
                ResponseError(
                    status=status if isinstance(status, int) else None,
                    message=message if isinstance(message, str) else None,
                )
            )
    return tuple(errors) or None


def envelope_message(body: Any) -> str | None:
    """Read the envelope's ``message``, if it has a usable one."""
    if isinstance(body, dict):
        message = body.get("message")
        if isinstance(message, str) and message:
            return message
    return None
