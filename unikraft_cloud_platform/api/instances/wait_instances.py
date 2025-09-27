from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.name_or_uuid import NameOrUUID
from ...models.wait_instance_response import WaitInstanceResponse
from ...models.wait_instances_state import WaitInstancesState
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: list["NameOrUUID"],
    state: Union[Unset, WaitInstancesState] = UNSET,
    timeout_ms: Union[Unset, int] = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    json_state: Union[Unset, str] = UNSET
    if not isinstance(state, Unset):
        json_state = state

    params["state"] = json_state

    params["timeout_ms"] = timeout_ms

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/instances/wait",
        "params": params,
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item = body_item_data.to_dict()
        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> WaitInstanceResponse:
    response_default = WaitInstanceResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[WaitInstanceResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
    state: Union[Unset, WaitInstancesState] = UNSET,
    timeout_ms: Union[Unset, int] = UNSET,
) -> Response[WaitInstanceResponse]:
    """Wait for Instances States

     Wait for one or more instances to reach certain states by ID(s)
    (name or UUID).

    If the instances are already in the desired states, the request will return
    immediately.  If the instances are not in the desired state, the request will
    block until the instances reach the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instances reach the desired states.

    Args:
        state (Union[Unset, WaitInstancesState]):
        timeout_ms (Union[Unset, int]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[WaitInstanceResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        state=state,
        timeout_ms=timeout_ms,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
    state: Union[Unset, WaitInstancesState] = UNSET,
    timeout_ms: Union[Unset, int] = UNSET,
) -> Optional[WaitInstanceResponse]:
    """Wait for Instances States

     Wait for one or more instances to reach certain states by ID(s)
    (name or UUID).

    If the instances are already in the desired states, the request will return
    immediately.  If the instances are not in the desired state, the request will
    block until the instances reach the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instances reach the desired states.

    Args:
        state (Union[Unset, WaitInstancesState]):
        timeout_ms (Union[Unset, int]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        WaitInstanceResponse
    """

    return sync_detailed(
        client=client,
        body=body,
        state=state,
        timeout_ms=timeout_ms,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
    state: Union[Unset, WaitInstancesState] = UNSET,
    timeout_ms: Union[Unset, int] = UNSET,
) -> Response[WaitInstanceResponse]:
    """Wait for Instances States

     Wait for one or more instances to reach certain states by ID(s)
    (name or UUID).

    If the instances are already in the desired states, the request will return
    immediately.  If the instances are not in the desired state, the request will
    block until the instances reach the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instances reach the desired states.

    Args:
        state (Union[Unset, WaitInstancesState]):
        timeout_ms (Union[Unset, int]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[WaitInstanceResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        state=state,
        timeout_ms=timeout_ms,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
    state: Union[Unset, WaitInstancesState] = UNSET,
    timeout_ms: Union[Unset, int] = UNSET,
) -> Optional[WaitInstanceResponse]:
    """Wait for Instances States

     Wait for one or more instances to reach certain states by ID(s)
    (name or UUID).

    If the instances are already in the desired states, the request will return
    immediately.  If the instances are not in the desired state, the request will
    block until the instances reach the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instances reach the desired states.

    Args:
        state (Union[Unset, WaitInstancesState]):
        timeout_ms (Union[Unset, int]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        WaitInstanceResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            state=state,
            timeout_ms=timeout_ms,
        )
    ).parsed
