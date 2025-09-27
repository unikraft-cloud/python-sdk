from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.update_instances_request import UpdateInstancesRequest
from ...models.update_instances_response import UpdateInstancesResponse
from ...types import Response


def _get_kwargs(
    *,
    body: UpdateInstancesRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/v1/instances",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> UpdateInstancesResponse:
    response_default = UpdateInstancesResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[UpdateInstancesResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: UpdateInstancesRequest,
) -> Response[UpdateInstancesResponse]:
    """Update Instances

     Update (modify) one or more instances by ID(s) (name or UUID).  The
    instances must be in a stopped state for most update operations.

    Args:
        body (UpdateInstancesRequest): The request message for updating one or more instances.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UpdateInstancesResponse]
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
    body: UpdateInstancesRequest,
) -> Optional[UpdateInstancesResponse]:
    """Update Instances

     Update (modify) one or more instances by ID(s) (name or UUID).  The
    instances must be in a stopped state for most update operations.

    Args:
        body (UpdateInstancesRequest): The request message for updating one or more instances.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UpdateInstancesResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: UpdateInstancesRequest,
) -> Response[UpdateInstancesResponse]:
    """Update Instances

     Update (modify) one or more instances by ID(s) (name or UUID).  The
    instances must be in a stopped state for most update operations.

    Args:
        body (UpdateInstancesRequest): The request message for updating one or more instances.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UpdateInstancesResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: UpdateInstancesRequest,
) -> Optional[UpdateInstancesResponse]:
    """Update Instances

     Update (modify) one or more instances by ID(s) (name or UUID).  The
    instances must be in a stopped state for most update operations.

    Args:
        body (UpdateInstancesRequest): The request message for updating one or more instances.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UpdateInstancesResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
