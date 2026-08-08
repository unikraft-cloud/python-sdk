# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# The plumbing transport: what goes on the wire, and what comes back off it.

from __future__ import annotations

import json
import warnings
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, Field

from unikraft_cloud import (
    Api,
    ApiClient,
    ApiClientConfig,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnikraftCloudError,
    UnikraftCloudWarning,
)
from unikraft_cloud.api.platform import PlatformApi
from unikraft_cloud.core.http import CommaSeparated, encode_body, encode_query

from .conftest import Recorder, envelope, queued, routed

BASE = "https://api.fra.unikraft.cloud"


class Env(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    op_time_us: int


class Page(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    from_: str | None = Field(default=None, alias="from")
    count: int | None = None
    name: str | None = None


class Client(ApiClient):
    """A stand-in for a generated client, exercising the transport directly."""

    async def read(self, **kwargs: Any) -> Env:
        return await self._request(Env, method="GET", path="/v1/things", **kwargs)

    async def write(self, body: Any) -> Env:
        return await self._request(Env, method="POST", path="/v1/things", body=body)

    async def discard(self) -> None:
        return await self._request_no_content(method="DELETE", path="/v1/things")

    def events(self) -> Any:
        return self._stream(dict, method="GET", path="/v1/events")


def client(recorder: Recorder, **config: Any) -> Client:
    return Client(
        ApiClientConfig(
            base_url="https://api.fra.unikraft.cloud/",
            token="tok",
            user_agent="unikraft-cloud-python/test",
            transport=recorder.transport,
            **config,
        )
    )


class TestRequests:
    async def test_sends_a_bearer_token_and_user_agent(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read()
        sent = recorder.calls[0]
        assert sent.headers["authorization"] == "Bearer tok"
        assert sent.headers["user-agent"] == "unikraft-cloud-python/test"
        assert sent.headers["accept"] == "application/json"

    async def test_strips_a_trailing_slash_from_the_base_url(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read()
        assert recorder.urls == ["https://api.fra.unikraft.cloud/v1/things"]

    async def test_a_per_call_base_url_redirects_one_request(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read(base_url="https://api.dal.unikraft.cloud")
            await api.read()
        assert recorder.urls == [
            "https://api.dal.unikraft.cloud/v1/things",
            "https://api.fra.unikraft.cloud/v1/things",
        ]

    async def test_drops_a_trailing_v1_the_operation_paths_already_carry(self) -> None:
        recorder = queued([(200, envelope())])
        api = Client(ApiClientConfig(base_url=f"{BASE}/v1", transport=recorder.transport))
        async with api:
            await api.read()
        assert recorder.urls == [f"{BASE}/v1/things"]

    async def test_a_per_call_base_url_drops_its_v1_too(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read(base_url="https://api.dal.unikraft.cloud/v1")
        assert recorder.urls == ["https://api.dal.unikraft.cloud/v1/things"]

    async def test_the_token_wins_over_a_caller_supplied_header(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read(headers={"authorization": "Bearer wrong", "x-extra": "1"})
        assert recorder.calls[0].headers["authorization"] == "Bearer tok"
        assert recorder.calls[0].headers["x-extra"] == "1"

    async def test_the_token_wins_whatever_the_header_is_cased(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder, headers={"X-Extra": "default"}) as api:
            await api.read(headers={"Authorization": "Bearer wrong", "x-extra": "1"})
        sent = recorder.calls[0]
        # One `authorization` header, not the token beside a rogue one.
        assert sent.headers.get_list("authorization") == ["Bearer tok"]
        assert sent.headers.get_list("x-extra") == ["1"]

    async def test_sends_no_body_on_a_get_without_one(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read()
        assert not recorder.calls[0].content
        assert "content-type" not in recorder.calls[0].headers

    async def test_sends_a_body_on_a_get_when_given_one(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read(body={"name": "policy"})
        sent = recorder.calls[0]
        assert json.loads(sent.content) == {"name": "policy"}
        assert sent.headers["content-type"] == "application/json"

    async def test_sends_a_json_body_on_a_post(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.write([{"name": "web"}])
        sent = recorder.calls[0]
        assert json.loads(sent.content) == [{"name": "web"}]
        assert sent.headers["content-type"] == "application/json"


class TestQueryEncoding:
    def test_repeats_a_list_as_one_parameter_per_item(self) -> None:
        assert str(encode_query({"uuid": ["a", "b"]})) == "uuid=a&uuid=b"

    def test_spells_booleans_lower_case(self) -> None:
        # `str(True)` would send `True`, which the API rejects.
        assert str(encode_query({"details": True, "raw": False})) == "details=true&raw=false"

    def test_drops_absent_values(self) -> None:
        assert encode_query({"a": None}) is None
        assert str(encode_query({"a": None, "b": 1})) == "b=1"

    def test_a_comma_separated_list_is_one_parameter(self) -> None:
        # The API splits on the comma before unescaping, so it stays literal.
        assert encode_query({"tags": CommaSeparated(["a:1", "b"])}) == "tags=a%3A1,b"

    def test_an_empty_comma_separated_list_filters_nothing(self) -> None:
        assert encode_query({"tags": CommaSeparated([])}) is None

    def test_no_parameters_at_all_is_no_query_string(self) -> None:
        assert encode_query(None) is None
        assert encode_query({}) is None


class TestBodyEncoding:
    def test_sends_only_the_fields_the_caller_set(self) -> None:
        assert json.loads(encode_body(Page(count=10))) == {"count": 10}

    def test_keeps_an_explicit_null(self) -> None:
        # The API distinguishes an absent field from a null one.
        assert json.loads(encode_body(Page(name=None))) == {"name": None}

    def test_uses_the_wire_name_for_a_renamed_field(self) -> None:
        assert json.loads(encode_body(Page(from_="u9"))) == {"from": "u9"}

    def test_accepts_the_wire_name_on_the_way_in_too(self) -> None:
        assert json.loads(encode_body(Page.model_validate({"from": "u1"}))) == {"from": "u1"}

    def test_encodes_lists_and_plain_dicts(self) -> None:
        assert json.loads(encode_body([Page(count=1), Page(count=2)])) == [
            {"count": 1},
            {"count": 2},
        ]
        assert json.loads(encode_body([{"name": "web"}])) == [{"name": "web"}]


class TestErrors:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (401, AuthenticationError),
            (403, AuthenticationError),
            (404, NotFoundError),
            (429, RateLimitError),
            (500, ServerError),
            (503, ServerError),
            (418, UnikraftCloudError),
        ],
    )
    async def test_maps_a_status_to_its_error_class(
        self, status: int, expected: type[UnikraftCloudError]
    ) -> None:
        recorder = queued([(status, {"status": "error", "message": "nope"})])
        async with client(recorder) as api:
            with pytest.raises(expected) as caught:
                await api.read()
        assert caught.value.status == status
        assert caught.value.kind == "http"
        assert str(caught.value) == "nope"

    async def test_carries_the_structured_errors(self) -> None:
        body = {
            "status": "error",
            "message": "bad",
            "errors": [{"status": 404, "message": "gone"}],
        }
        recorder = queued([(400, body)])
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                await api.read()
        assert caught.value.errors is not None
        assert caught.value.errors[0].status == 404
        assert caught.value.errors[0].message == "gone"
        assert caught.value.body == body

    async def test_falls_back_to_the_status_when_there_is_no_message(self) -> None:
        recorder = queued([(500, {"status": "error"})])
        async with client(recorder) as api:
            with pytest.raises(ServerError) as caught:
                await api.read()
        assert "500" in str(caught.value)

    async def test_a_redirect_is_a_failure_not_a_result(self) -> None:
        # Redirects are not followed, so a 3xx that reaches the client is an
        # answer it cannot use, however well its body validates.
        recorder = queued([(302, envelope())])
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                await api.read()
        assert caught.value.status == 302
        assert caught.value.kind == "http"

    async def test_unparseable_body_on_a_redirect_reports_the_status(self) -> None:
        recorder = Recorder(lambda request: httpx.Response(302, content=b"<html>moved"))
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                await api.read()
        assert caught.value.kind == "http"
        assert caught.value.status == 302

    async def test_unparseable_body_on_a_failure_reports_the_status(self) -> None:
        recorder = Recorder(lambda request: httpx.Response(502, content=b"<html>oops"))
        async with client(recorder) as api:
            with pytest.raises(ServerError) as caught:
                await api.read()
        assert caught.value.kind == "http"
        assert caught.value.body == "<html>oops"

    async def test_unparseable_body_on_a_success_is_a_parse_failure(self) -> None:
        recorder = Recorder(lambda request: httpx.Response(200, content=b"not json"))
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                await api.read()
        assert caught.value.kind == "parse"

    async def test_a_response_that_contradicts_the_spec_is_a_parse_failure(self) -> None:
        recorder = queued([(200, {"status": "success"})])  # op_time_us is required
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                await api.read()
        assert caught.value.kind == "parse"
        assert "op_time_us" in str(caught.value)

    async def test_a_transport_failure_is_a_network_error(self) -> None:
        def boom(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        recorder = Recorder(boom)
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                await api.read()
        assert caught.value.kind == "network"
        assert "connection refused" in str(caught.value)

    async def test_every_error_is_catchable_as_one_type(self) -> None:
        recorder = queued([(404, {"status": "error", "message": "gone"})])
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError):
                await api.read()


class TestApiWarnings:
    async def test_a_warning_the_api_sends_reaches_the_caller(self) -> None:
        body = envelope(warnings=[{"type": "deprecated", "message": "`cn` is deprecated"}])
        recorder = queued([(200, body)])
        async with client(recorder) as api:
            with pytest.warns(UnikraftCloudWarning, match="`cn` is deprecated"):
                await api.read()

    async def test_an_answer_without_warnings_is_quiet(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                await api.read()


class TestNoContent:
    async def test_ignores_the_payload(self) -> None:
        recorder = queued([(200, envelope({"anything": 1}))])
        async with client(recorder) as api:
            await api.discard()
        assert recorder.paths == ["/v1/things"]

    async def test_still_raises_on_a_failure(self) -> None:
        recorder = queued([(403, {"status": "error", "message": "denied"})])
        async with client(recorder) as api:
            with pytest.raises(AuthenticationError):
                await api.discard()

    async def test_still_raises_on_a_redirect(self) -> None:
        recorder = queued([(302, envelope())])
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                await api.discard()
        assert caught.value.status == 302


class TestEventStreams:
    def _stream(self, body: bytes) -> Recorder:
        return Recorder(
            lambda request: httpx.Response(
                200, content=body, headers={"content-type": "text/event-stream"}
            )
        )

    async def test_yields_each_events_payload(self) -> None:
        recorder = self._stream(b'data: {"n": 1}\n\ndata: {"n": 2}\n\n')
        async with client(recorder) as api:
            assert [event async for event in api.events()] == [{"n": 1}, {"n": 2}]
        assert recorder.calls[0].headers["accept"] == "text/event-stream"

    async def test_skips_comments_and_keep_alives(self) -> None:
        recorder = self._stream(b': keep-alive\n\ndata: {"n": 1}\n\n\n\n')
        async with client(recorder) as api:
            assert [event async for event in api.events()] == [{"n": 1}]

    async def test_yields_a_last_event_with_no_trailing_blank_line(self) -> None:
        recorder = self._stream(b'data: {"n": 1}\n\ndata: {"n": 2}')
        async with client(recorder) as api:
            assert [event async for event in api.events()] == [{"n": 1}, {"n": 2}]

    async def test_joins_a_multi_line_payload(self) -> None:
        recorder = self._stream(b'data: {"n":\ndata:  1}\n\n')
        async with client(recorder) as api:
            assert [event async for event in api.events()] == [{"n": 1}]

    async def test_joins_a_multi_line_payload_split_by_carriage_returns(self) -> None:
        recorder = self._stream(b'data: {"n":\rdata:  1}\r\r')
        async with client(recorder) as api:
            assert [event async for event in api.events()] == [{"n": 1}]

    async def test_keeps_the_line_separators_a_payload_carries(self) -> None:
        # JSON leaves U+2028 and U+2029 unescaped; neither ends an event line.
        recorder = self._stream('data: {"n": "a\u2028b\u2029c"}\n\n'.encode())
        async with client(recorder) as api:
            assert [event async for event in api.events()] == [{"n": "a\u2028b\u2029c"}]

    async def test_reports_an_unparseable_event(self) -> None:
        recorder = self._stream(b"data: {oops\n\n")
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                [event async for event in api.events()]
        assert caught.value.kind == "parse"

    async def test_a_failed_stream_raises_before_yielding(self) -> None:
        recorder = Recorder(
            lambda request: httpx.Response(403, json={"status": "error", "message": "denied"})
        )
        async with client(recorder) as api:
            with pytest.raises(AuthenticationError):
                [event async for event in api.events()]

    async def test_a_redirected_stream_raises_before_yielding(self) -> None:
        recorder = Recorder(
            lambda request: httpx.Response(
                302, content=b'data: {"n": 1}\n\n', headers={"location": "https://elsewhere"}
            )
        )
        async with client(recorder) as api:
            with pytest.raises(UnikraftCloudError) as caught:
                [event async for event in api.events()]
        assert caught.value.status == 302

    async def test_a_stream_that_breaks_mid_body_is_a_network_error(self) -> None:
        class Broken(httpx.AsyncByteStream):
            async def __aiter__(self) -> Any:
                yield b'data: {"n": 1}\n\n'
                raise httpx.ReadError("connection reset")

        recorder = Recorder(
            lambda request: httpx.Response(
                200, stream=Broken(), headers={"content-type": "text/event-stream"}
            )
        )
        async with client(recorder) as api:
            seen: list[Any] = []
            with pytest.raises(UnikraftCloudError) as caught:
                async for event in api.events():
                    seen.append(event)
        assert seen == [{"n": 1}]
        assert caught.value.kind == "network"
        assert "connection reset" in str(caught.value)

    async def test_breaking_early_releases_the_stream(self) -> None:
        recorder = self._stream(b'data: {"n": 1}\n\ndata: {"n": 2}\n\n')
        async with client(recorder) as api:
            async for _ in api.events():
                break


class TestLifecycle:
    async def test_closes_the_pool_it_created(self) -> None:
        recorder = queued([(200, envelope())])
        api = client(recorder)
        assert not api.http.is_closed
        await api.aclose()
        assert api.http.is_closed

    async def test_leaves_an_injected_client_alone(self) -> None:
        recorder = queued([(200, envelope())])
        async with httpx.AsyncClient(transport=recorder.transport) as http:
            api = Client(ApiClientConfig(base_url="https://api.fra.unikraft.cloud", http=http))
            await api.aclose()
            assert not http.is_closed

    async def test_shares_one_pool_across_clients(self) -> None:
        recorder = queued([(200, envelope())])
        async with httpx.AsyncClient(transport=recorder.transport) as http:
            config = ApiClientConfig(base_url="https://api.fra.unikraft.cloud", http=http)
            assert Client(config).http is Client(config).http

    async def test_a_group_shares_one_pool_and_closes_it(self) -> None:
        recorder = queued([(200, envelope())])
        api = PlatformApi(
            ApiClientConfig(base_url="https://api.fra.unikraft.cloud", transport=recorder.transport)
        )
        assert api.instances.http is api.volumes.http is api.http
        async with api:
            pass
        assert api.http.is_closed

    async def test_a_group_leaves_an_injected_client_alone(self) -> None:
        recorder = queued([(200, envelope())])
        async with httpx.AsyncClient(transport=recorder.transport) as http:
            api = PlatformApi(ApiClientConfig(base_url="https://api.fra.unikraft.cloud", http=http))
            assert api.instances.http is http
            await api.aclose()
            assert not http.is_closed


class TestApiSurfaces:
    async def test_the_control_plane_keeps_its_own_transport(self) -> None:
        platform_calls = queued([(200, envelope())])
        control_calls = queued([(200, envelope({"metros": []}))])
        api = Api(
            ApiClientConfig(
                base_url="https://api.fra.unikraft.cloud", transport=platform_calls.transport
            ),
            ApiClientConfig(base_url="https://cp.example", transport=control_calls.transport),
        )
        async with api:
            await api.controlplane.metros.list_metros()
        assert len(control_calls.calls) == 1
        assert platform_calls.calls == []

    async def test_both_surfaces_share_one_pool_by_default(self) -> None:
        recorder = queued([(200, envelope())])
        config = ApiClientConfig(
            base_url="https://api.fra.unikraft.cloud", transport=recorder.transport
        )
        api = Api(config, config.with_base_url("https://cp.example"))
        assert api.platform.instances.http is api.controlplane.metros.http
        await api.aclose()
        assert api.platform.instances.http.is_closed


class TestClosedClients:
    async def test_a_closed_client_says_so(self) -> None:
        recorder = queued([(200, envelope())])
        api = client(recorder)
        await api.aclose()
        with pytest.raises(UnikraftCloudError, match="closed") as caught:
            await api.read()
        assert caught.value.kind == "network"


class TestTimeouts:
    async def test_bounds_connecting_but_not_reading_by_default(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder) as api:
            await api.read()
        # `wait` operations block for minutes, so only connecting is bounded.
        sent = recorder.calls[0].extensions["timeout"]
        assert sent["read"] is None
        assert sent["connect"] == 10.0

    def test_each_config_gets_a_timeout_of_its_own(self) -> None:
        one = ApiClientConfig(base_url=BASE)
        two = ApiClientConfig(base_url=BASE)
        assert isinstance(one.timeout, httpx.Timeout)
        # `httpx.Timeout` is mutable, so one config's is not everyone else's.
        one.timeout.connect = 0.5
        assert two.timeout != one.timeout

    async def test_uses_the_configured_timeout_by_default(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder, timeout=7.0) as api:
            await api.read()
        assert recorder.calls[0].extensions["timeout"]["read"] == 7.0

    async def test_a_per_call_timeout_overrides_it(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder, timeout=7.0) as api:
            await api.read(timeout=1.5)
        assert recorder.calls[0].extensions["timeout"]["read"] == 1.5

    async def test_an_explicit_none_means_no_timeout(self) -> None:
        recorder = queued([(200, envelope())])
        async with client(recorder, timeout=7.0) as api:
            await api.read(timeout=None)
        assert recorder.calls[0].extensions["timeout"]["read"] is None


async def test_routed_transport_answers_per_url() -> None:
    recorder = routed(lambda request: (200, envelope({"where": request.url.host.split(".")[1]})))
    async with client(recorder) as api:
        one = await api.read()
        two = await api.read(base_url="https://api.dal.unikraft.cloud")
    assert one.model_extra is not None
    assert one.model_extra["data"] == {"where": "fra"}
    assert two.model_extra is not None
    assert two.model_extra["data"] == {"where": "dal"}
