# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.
#
# Shared, spec-independent HTTP transport for the generated plumbing clients.

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass, replace
from types import TracebackType
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError
from typing_extensions import NotRequired, Self, TypedDict

from .errors import (
    UnikraftCloudError,
    envelope_message,
    error_for_status,
    parse_response_errors,
)

__all__ = [
    "UNSET",
    "ApiClient",
    "ApiClientConfig",
    "CallOptions",
    "QueryValue",
    "TimeoutOption",
    "Unset",
]

T = TypeVar("T")

#: A value that can be serialised into a query string.
QueryValue = str | int | float | bool | Sequence[str | int | float | bool] | None

# The Fetch-based JavaScript SDK sends no timeout at all, and the platform API's
# `wait` operations legitimately block for minutes. A read timeout would break
# them, so only connecting is bounded.
DEFAULT_TIMEOUT = httpx.Timeout(None, connect=10.0)


class Unset:
    """The absence of an argument, where ``None`` is itself a meaningful value.

    A per-call ``timeout=None`` means "no timeout"; omitting it means "use the
    client's". The two need different values to be told apart.
    """

    __slots__ = ()


UNSET = Unset()

#: A per-call timeout override. Omitted, the client's own timeout applies.
TimeoutOption = float | httpx.Timeout | Unset | None


class CallOptions(TypedDict):
    """Per-call options accepted by every generated operation."""

    #: Extra headers merged over the client defaults for this call only.
    headers: NotRequired[Mapping[str, str] | None]
    #: Override the base URL (e.g. to target a different metro) for this call.
    base_url: NotRequired[str | None]
    #: Override the client's timeout for this call.
    timeout: NotRequired[float | httpx.Timeout | None]


@dataclass(frozen=True)
class ApiClientConfig:
    """Configuration for the plumbing :class:`ApiClient`."""

    #: Fully-qualified API base URL, e.g. ``https://api.fra.unikraft.cloud``.
    base_url: str
    #: Bearer token used for authentication.
    token: str | None = None
    #: Default headers sent with every request.
    headers: Mapping[str, str] | None = None
    #: User-Agent value sent with every request.
    user_agent: str | None = None
    #: An httpx client to send through. When omitted the client makes its own
    #: and closes it on `aclose()`; sharing one across clients shares its pool.
    http: httpx.AsyncClient | None = None
    #: Transport for the client to build itself around, chiefly for testing
    #: (`httpx.MockTransport`). Ignored when `http` is given.
    transport: httpx.AsyncBaseTransport | None = None
    #: Honour the `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` environment variables.
    trust_env: bool = True
    #: Timeout applied to every request. `httpx.Timeout` is mutable, so this
    #: needs a factory rather than a shared default instance.
    timeout: float | httpx.Timeout | None = field(default_factory=lambda: DEFAULT_TIMEOUT)

    def with_base_url(self, base_url: str) -> ApiClientConfig:
        """This configuration pointed at another endpoint, e.g. another metro."""
        return replace(self, base_url=base_url)


#: Separator between two server-sent events (``\n\n``, ``\r\n\r\n`` or ``\r\r``).
_SSE_EVENT_BOUNDARY = re.compile(r"\r\n\r\n|\n\n|\r\r")


def _sse_data(block: str) -> str | None:
    """Extract the payload of one server-sent event block.

    The payload is the concatenation of the block's ``data:`` field values.
    Returns ``None`` for blocks without any (comments and keep-alives), which
    the caller skips.
    """
    values: list[str] = []
    for raw_line in block.split("\n"):
        line = raw_line[:-1] if raw_line.endswith("\r") else raw_line
        # A leading colon marks a comment (used for keep-alives).
        if line.startswith(":"):
            continue
        colon = line.find(":")
        if (line if colon == -1 else line[:colon]) != "data":
            continue
        value = "" if colon == -1 else line[colon + 1 :]
        values.append(value[1:] if value.startswith(" ") else value)
    return "\n".join(values) if values else None


def encode_query(query: Mapping[str, QueryValue] | None) -> httpx.QueryParams | None:
    """Serialise a query mapping into form/explode style parameters.

    A list becomes one repeated parameter per item, which is how the platform
    API spells its filters (``?uuid=a&uuid=b``).
    """
    if not query:
        return None
    # httpx types its pair list over every scalar it accepts, and `list` is
    # invariant, so the annotation has to be the wider one even though every
    # value put in is a `str`.
    params: list[tuple[str, str | int | float | bool | None]] = []
    for key, value in query.items():
        if value is None:
            continue
        # `str` is a Sequence, so it has to be excluded before the list case.
        if isinstance(value, (list, tuple)):
            params.extend((key, _query_scalar(item)) for item in value)
        else:
            params.append((key, _query_scalar(value)))
    return httpx.QueryParams(params) if params else None


def encode_body(body: Any) -> bytes:
    """Serialise a request body to JSON.

    Generated request models are dumped by alias and without the fields the
    caller never set, so a body carries exactly what was asked for: the API
    treats an absent field and a null one differently, and a model's defaults
    are the SDK's opinion rather than the caller's.
    """
    return json.dumps(_jsonable(body)).encode()


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True, exclude_unset=True)
    if isinstance(value, Mapping):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _jsonable(getattr(value, f.name)) for f in fields(value)}
    return value


def _query_scalar(value: object) -> str:
    # JSON and every other API client spell booleans lower-case; `str(True)`
    # would send `True`, which the API rejects.
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def describe_cause(err: BaseException) -> str:
    """Build a readable message from an exception and its cause chain.

    httpx reports a bare ``ConnectError``; the useful detail (e.g.
    ``ECONNREFUSED``, or a TLS certificate error from a MITM proxy) lives in
    nested causes.
    """
    parts: list[str] = []
    current: BaseException | None = err
    for _ in range(6):
        if current is None:
            break
        text = str(current)
        if text and text not in parts:
            parts.append(text)
        current = current.__cause__ or current.__context__
    return ": ".join(parts) if parts else repr(err)


class ApiClient:
    """Base transport for the generated resource clients.

    Performs authenticated requests and returns the parsed response envelope.
    Raises :class:`UnikraftCloudError` on network failures and non-2xx HTTP
    responses.
    """

    def __init__(self, config: ApiClientConfig) -> None:
        self._config = config
        self._base_url = config.base_url.rstrip("/")
        self._default_headers: dict[str, str] = dict(config.headers or {})
        if config.user_agent:
            self._default_headers["user-agent"] = config.user_agent
        self._owns_http = config.http is None
        self._http = config.http or httpx.AsyncClient(
            transport=config.transport,
            trust_env=config.trust_env,
            timeout=config.timeout,
        )

    @property
    def http(self) -> httpx.AsyncClient:
        """The httpx client this transport sends through."""
        return self._http

    async def aclose(self) -> None:
        """Release the connection pool, if this client is the one that made it."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    def _build_request(
        self,
        *,
        method: str,
        path: str,
        accept: str,
        query: Mapping[str, QueryValue] | None,
        body: Any,
        headers: Mapping[str, str] | None,
        base_url: str | None,
        timeout: TimeoutOption,
    ) -> httpx.Request:
        base = (base_url or self._base_url).rstrip("/")

        merged: dict[str, str] = {"accept": accept, **self._default_headers}
        if headers:
            merged.update(headers)
        # The token is applied last: a caller's own `authorization` header would
        # otherwise silently deauthenticate the request.
        if self._config.token:
            merged["authorization"] = f"Bearer {self._config.token}"

        method = method.upper()
        content: bytes | None = None
        # No HTTP client will send a body on GET or HEAD, and the API models the
        # filters for those operations as query parameters too.
        if method not in ("GET", "HEAD") and body is not None:
            content = encode_body(body)
            merged["content-type"] = "application/json"

        return self._http.build_request(
            method,
            base + path,
            params=encode_query(query),
            content=content,
            headers=merged,
            timeout=self._config.timeout if isinstance(timeout, Unset) else timeout,
        )

    async def _send(self, request: httpx.Request, *, stream: bool) -> httpx.Response:
        try:
            return await self._http.send(request, stream=stream)
        except httpx.HTTPError as cause:
            raise UnikraftCloudError(
                f"Request to {request.url} failed: {describe_cause(cause)}",
                kind="network",
            ) from cause

    async def _request(
        self,
        model: type[T],
        *,
        method: str,
        path: str,
        query: Mapping[str, QueryValue] | None = None,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> T:
        """Perform a request and return its response envelope parsed as `model`."""
        request = self._build_request(
            method=method,
            path=path,
            accept="application/json",
            query=query,
            body=body,
            headers=headers,
            base_url=base_url,
            timeout=timeout,
        )
        response = await self._send(request, stream=False)
        parsed = self._parse_json(response, request.url)
        self._raise_for_status(response, parsed)
        try:
            return TypeAdapter(model).validate_python(parsed)
        except ValidationError as cause:
            raise UnikraftCloudError(
                f"Response from {request.url} did not match the specification: {cause}",
                kind="parse",
                status=response.status_code,
                body=parsed,
            ) from cause

    async def _request_no_content(
        self,
        *,
        method: str,
        path: str,
        query: Mapping[str, QueryValue] | None = None,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> None:
        """Perform a request whose response carries no payload worth parsing."""
        request = self._build_request(
            method=method,
            path=path,
            accept="application/json",
            query=query,
            body=body,
            headers=headers,
            base_url=base_url,
            timeout=timeout,
        )
        response = await self._send(request, stream=False)
        self._raise_for_status(response, self._parse_json(response, request.url))

    async def _stream(
        self,
        model: type[T],
        *,
        method: str,
        path: str,
        query: Mapping[str, QueryValue] | None = None,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> AsyncIterator[T]:
        """Yield each event of a ``text/event-stream`` response, parsed as `model`.

        The iterator ends when the server closes the stream; ``break`` out of the
        loop to stop early and release the connection.
        """
        request = self._build_request(
            method=method,
            path=path,
            accept="text/event-stream",
            query=query,
            body=body,
            headers=headers,
            base_url=base_url,
            timeout=timeout,
        )
        response = await self._send(request, stream=True)
        try:
            if response.status_code >= 400:
                await response.aread()
                self._raise_for_status(response, self._parse_json(response, request.url))

            adapter = TypeAdapter(model)
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while match := _SSE_EVENT_BOUNDARY.search(buffer):
                    block, buffer = buffer[: match.start()], buffer[match.end() :]
                    event = self._parse_event(adapter, block, request.url, response.status_code)
                    if event is not None:
                        yield event
            # A last event may arrive without its trailing blank line.
            event = self._parse_event(adapter, buffer, request.url, response.status_code)
            if event is not None:
                yield event
        finally:
            # Close on early return or raise so the connection is not left
            # dangling mid-stream.
            await response.aclose()

    def _parse_event(
        self,
        adapter: TypeAdapter[T],
        block: str,
        url: httpx.URL,
        status: int,
    ) -> T | None:
        data = _sse_data(block)
        if not data:
            return None
        try:
            return adapter.validate_json(data)
        except (ValidationError, ValueError) as cause:
            raise UnikraftCloudError(
                f"Failed to parse event stream from {url}",
                kind="parse",
                status=status,
                body=data,
            ) from cause

    def _parse_json(self, response: httpx.Response, url: httpx.URL) -> Any:
        """Decode the response body, distinguishing a bad status from bad JSON."""
        text = response.text
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError as cause:
            if response.status_code >= 400:
                raise error_for_status(
                    response.status_code,
                    f"HTTP {response.status_code} {response.reason_phrase}",
                    body=text,
                ) from cause
            raise UnikraftCloudError(
                f"Failed to parse response body from {url}",
                kind="parse",
                status=response.status_code,
                body=text,
            ) from cause

    def _raise_for_status(self, response: httpx.Response, parsed: Any) -> None:
        if response.status_code < 400:
            return
        raise error_for_status(
            response.status_code,
            envelope_message(parsed) or f"HTTP {response.status_code} {response.reason_phrase}",
            errors=parse_response_errors(parsed),
            body=parsed,
        )
