from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.update_service_groups_request_item import UpdateServiceGroupsRequestItem
from ...models.update_service_groups_response import UpdateServiceGroupsResponse
from ...types import Response


def _get_kwargs(
    *,
    body: list["UpdateServiceGroupsRequestItem"],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/v1/services",
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item = body_item_data.to_dict()
        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> UpdateServiceGroupsResponse:
    response_default = UpdateServiceGroupsResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[UpdateServiceGroupsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["UpdateServiceGroupsRequestItem"],
) -> Response[UpdateServiceGroupsResponse]:
    """Update Service Groups

     Update one or more service groups.

    Args:
        body (list['UpdateServiceGroupsRequestItem']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UpdateServiceGroupsResponse]
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
    body: list["UpdateServiceGroupsRequestItem"],
) -> Optional[UpdateServiceGroupsResponse]:
    """Update Service Groups

     Update one or more service groups.

    Args:
        body (list['UpdateServiceGroupsRequestItem']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UpdateServiceGroupsResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["UpdateServiceGroupsRequestItem"],
) -> Response[UpdateServiceGroupsResponse]:
    """Update Service Groups

     Update one or more service groups.

    Args:
        body (list['UpdateServiceGroupsRequestItem']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UpdateServiceGroupsResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["UpdateServiceGroupsRequestItem"],
) -> Optional[UpdateServiceGroupsResponse]:
    """Update Service Groups

     Update one or more service groups.

    Args:
        body (list['UpdateServiceGroupsRequestItem']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UpdateServiceGroupsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
