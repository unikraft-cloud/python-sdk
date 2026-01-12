from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_service_group_request import CreateServiceGroupRequest
from ...models.create_service_group_response import CreateServiceGroupResponse
from ...types import Response


def _get_kwargs(
    *,
    body: CreateServiceGroupRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/services",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> CreateServiceGroupResponse:
    response_default = CreateServiceGroupResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[CreateServiceGroupResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateServiceGroupRequest,
) -> Response[CreateServiceGroupResponse]:
    """Create Service Group

     Create a new service with the given configuration.

    Note that the service properties like published ports can only be defined
    during creation.  They cannot be changed later.  Each port in a service can
    specify a list of handlers that determine how traffic arriving at the port
    is handled. See Connection Handlers for a complete overview.

    Args:
        body (CreateServiceGroupRequest): The request message for creating a new service group.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateServiceGroupResponse]
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
    body: CreateServiceGroupRequest,
) -> Optional[CreateServiceGroupResponse]:
    """Create Service Group

     Create a new service with the given configuration.

    Note that the service properties like published ports can only be defined
    during creation.  They cannot be changed later.  Each port in a service can
    specify a list of handlers that determine how traffic arriving at the port
    is handled. See Connection Handlers for a complete overview.

    Args:
        body (CreateServiceGroupRequest): The request message for creating a new service group.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateServiceGroupResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateServiceGroupRequest,
) -> Response[CreateServiceGroupResponse]:
    """Create Service Group

     Create a new service with the given configuration.

    Note that the service properties like published ports can only be defined
    during creation.  They cannot be changed later.  Each port in a service can
    specify a list of handlers that determine how traffic arriving at the port
    is handled. See Connection Handlers for a complete overview.

    Args:
        body (CreateServiceGroupRequest): The request message for creating a new service group.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateServiceGroupResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateServiceGroupRequest,
) -> Optional[CreateServiceGroupResponse]:
    """Create Service Group

     Create a new service with the given configuration.

    Note that the service properties like published ports can only be defined
    during creation.  They cannot be changed later.  Each port in a service can
    specify a list of handlers that determine how traffic arriving at the port
    is handled. See Connection Handlers for a complete overview.

    Args:
        body (CreateServiceGroupRequest): The request message for creating a new service group.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateServiceGroupResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
