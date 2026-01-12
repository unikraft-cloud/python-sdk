from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_autoscale_configurations_request_configuration import (
    CreateAutoscaleConfigurationsRequestConfiguration,
)
from ...models.create_autoscale_configurations_response import CreateAutoscaleConfigurationsResponse
from ...types import Response


def _get_kwargs(
    *,
    body: list["CreateAutoscaleConfigurationsRequestConfiguration"],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/services/autoscale",
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
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["CreateAutoscaleConfigurationsRequestConfiguration"],
) -> Response[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configurations

     Create one or more autoscale configurations for the specified service groups
    given their UUIDs or names.

    Args:
        body (list['CreateAutoscaleConfigurationsRequestConfiguration']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAutoscaleConfigurationsResponse]
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
    body: list["CreateAutoscaleConfigurationsRequestConfiguration"],
) -> Optional[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configurations

     Create one or more autoscale configurations for the specified service groups
    given their UUIDs or names.

    Args:
        body (list['CreateAutoscaleConfigurationsRequestConfiguration']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAutoscaleConfigurationsResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["CreateAutoscaleConfigurationsRequestConfiguration"],
) -> Response[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configurations

     Create one or more autoscale configurations for the specified service groups
    given their UUIDs or names.

    Args:
        body (list['CreateAutoscaleConfigurationsRequestConfiguration']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAutoscaleConfigurationsResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["CreateAutoscaleConfigurationsRequestConfiguration"],
) -> Optional[CreateAutoscaleConfigurationsResponse]:
    """Create Autoscale Configurations

     Create one or more autoscale configurations for the specified service groups
    given their UUIDs or names.

    Args:
        body (list['CreateAutoscaleConfigurationsRequestConfiguration']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAutoscaleConfigurationsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
