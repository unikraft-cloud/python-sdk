from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_instances_response import GetInstancesResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    uuid: UUID,
    *,
    details: Union[Unset, bool] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["details"] = details

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/v1/instances/{uuid}",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> GetInstancesResponse:
    response_default = GetInstancesResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetInstancesResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    details: Union[Unset, bool] = UNSET,
) -> Response[GetInstancesResponse]:
    """Get Instance by UUID

     Get a single instance by its UUID.

    Args:
        uuid (UUID):
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstancesResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        details=details,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    details: Union[Unset, bool] = UNSET,
) -> Optional[GetInstancesResponse]:
    """Get Instance by UUID

     Get a single instance by its UUID.

    Args:
        uuid (UUID):
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstancesResponse
    """

    return sync_detailed(
        uuid=uuid,
        client=client,
        details=details,
    ).parsed


async def asyncio_detailed(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    details: Union[Unset, bool] = UNSET,
) -> Response[GetInstancesResponse]:
    """Get Instance by UUID

     Get a single instance by its UUID.

    Args:
        uuid (UUID):
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstancesResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        details=details,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    details: Union[Unset, bool] = UNSET,
) -> Optional[GetInstancesResponse]:
    """Get Instance by UUID

     Get a single instance by its UUID.

    Args:
        uuid (UUID):
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstancesResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            details=details,
        )
    ).parsed
