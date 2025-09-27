from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_autoscale_configuration_policy_request import CreateAutoscaleConfigurationPolicyRequest
from ...models.create_autoscale_configuration_policy_response import CreateAutoscaleConfigurationPolicyResponse
from ...types import Response


def _get_kwargs(
    uuid: str,
    *,
    body: CreateAutoscaleConfigurationPolicyRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/v1/services/{uuid}/autoscale/policies",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> CreateAutoscaleConfigurationPolicyResponse:
    response_default = CreateAutoscaleConfigurationPolicyResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[CreateAutoscaleConfigurationPolicyResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    uuid: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateAutoscaleConfigurationPolicyRequest,
) -> Response[CreateAutoscaleConfigurationPolicyResponse]:
    """Create Autoscale Configuration Policy

     Add a new autoscale policy to an autoscale configuration given a service
    group UUID.

    Args:
        uuid (str):
        body (CreateAutoscaleConfigurationPolicyRequest): The request message to create an
            autoscale configuration policy for a
            service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAutoscaleConfigurationPolicyResponse]
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
    uuid: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateAutoscaleConfigurationPolicyRequest,
) -> Optional[CreateAutoscaleConfigurationPolicyResponse]:
    """Create Autoscale Configuration Policy

     Add a new autoscale policy to an autoscale configuration given a service
    group UUID.

    Args:
        uuid (str):
        body (CreateAutoscaleConfigurationPolicyRequest): The request message to create an
            autoscale configuration policy for a
            service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAutoscaleConfigurationPolicyResponse
    """

    return sync_detailed(
        uuid=uuid,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    uuid: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateAutoscaleConfigurationPolicyRequest,
) -> Response[CreateAutoscaleConfigurationPolicyResponse]:
    """Create Autoscale Configuration Policy

     Add a new autoscale policy to an autoscale configuration given a service
    group UUID.

    Args:
        uuid (str):
        body (CreateAutoscaleConfigurationPolicyRequest): The request message to create an
            autoscale configuration policy for a
            service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAutoscaleConfigurationPolicyResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    uuid: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateAutoscaleConfigurationPolicyRequest,
) -> Optional[CreateAutoscaleConfigurationPolicyResponse]:
    """Create Autoscale Configuration Policy

     Add a new autoscale policy to an autoscale configuration given a service
    group UUID.

    Args:
        uuid (str):
        body (CreateAutoscaleConfigurationPolicyRequest): The request message to create an
            autoscale configuration policy for a
            service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAutoscaleConfigurationPolicyResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            body=body,
        )
    ).parsed
