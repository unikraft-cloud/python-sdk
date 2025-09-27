from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_autoscale_configuration_by_service_group_uuid_request import (
    CreateAutoscaleConfigurationByServiceGroupUUIDRequest,
)
from ...models.create_autoscale_configurations_response import CreateAutoscaleConfigurationsResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
    *,
    body: CreateAutoscaleConfigurationByServiceGroupUUIDRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/v1/services/{uuid}/autoscale",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> CreateAutoscaleConfigurationsResponse:
    response_default = CreateAutoscaleConfigurationsResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[CreateAutoscaleConfigurationsResponse]:
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
    body: CreateAutoscaleConfigurationByServiceGroupUUIDRequest,
) -> Response[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configuration by Service Group UUID

     Create an autoscale configuration for the specified service group given
    its UUID.

    Args:
        uuid (UUID):
        body (CreateAutoscaleConfigurationByServiceGroupUUIDRequest): The request message to
            create an autoscale configuration for a service group
            based on its UUID.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAutoscaleConfigurationsResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateAutoscaleConfigurationByServiceGroupUUIDRequest,
) -> Optional[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configuration by Service Group UUID

     Create an autoscale configuration for the specified service group given
    its UUID.

    Args:
        uuid (UUID):
        body (CreateAutoscaleConfigurationByServiceGroupUUIDRequest): The request message to
            create an autoscale configuration for a service group
            based on its UUID.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAutoscaleConfigurationsResponse
    """

    return sync_detailed(
        uuid=uuid,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateAutoscaleConfigurationByServiceGroupUUIDRequest,
) -> Response[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configuration by Service Group UUID

     Create an autoscale configuration for the specified service group given
    its UUID.

    Args:
        uuid (UUID):
        body (CreateAutoscaleConfigurationByServiceGroupUUIDRequest): The request message to
            create an autoscale configuration for a service group
            based on its UUID.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAutoscaleConfigurationsResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateAutoscaleConfigurationByServiceGroupUUIDRequest,
) -> Optional[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configuration by Service Group UUID

     Create an autoscale configuration for the specified service group given
    its UUID.

    Args:
        uuid (UUID):
        body (CreateAutoscaleConfigurationByServiceGroupUUIDRequest): The request message to
            create an autoscale configuration for a service group
            based on its UUID.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAutoscaleConfigurationsResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            body=body,
        )
    ).parsed
