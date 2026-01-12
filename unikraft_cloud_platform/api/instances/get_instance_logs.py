from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_instance_logs_request import GetInstanceLogsRequest
from ...models.get_instance_logs_response import GetInstanceLogsResponse
from ...types import Response


def _get_kwargs(
    *,
    body: GetInstanceLogsRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/instances/log",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> GetInstanceLogsResponse:
    response_default = GetInstanceLogsResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetInstanceLogsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: GetInstanceLogsRequest,
) -> Response[GetInstanceLogsResponse]:
    """Get Instances Logs

     Retrieve the logs of one or more instances by ID(s) (name or UUID).

    Args:
        body (GetInstanceLogsRequest): The request message for getting the logs of an instance by
            their UUID or
            name.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstanceLogsResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: GetInstanceLogsRequest,
) -> Optional[GetInstanceLogsResponse]:
    """Get Instances Logs

     Retrieve the logs of one or more instances by ID(s) (name or UUID).

    Args:
        body (GetInstanceLogsRequest): The request message for getting the logs of an instance by
            their UUID or
            name.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstanceLogsResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: GetInstanceLogsRequest,
) -> Response[GetInstanceLogsResponse]:
    """Get Instances Logs

     Retrieve the logs of one or more instances by ID(s) (name or UUID).

    Args:
        body (GetInstanceLogsRequest): The request message for getting the logs of an instance by
            their UUID or
            name.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstanceLogsResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: GetInstanceLogsRequest,
) -> Optional[GetInstanceLogsResponse]:
    """Get Instances Logs

     Retrieve the logs of one or more instances by ID(s) (name or UUID).

    Args:
        body (GetInstanceLogsRequest): The request message for getting the logs of an instance by
            their UUID or
            name.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstanceLogsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
