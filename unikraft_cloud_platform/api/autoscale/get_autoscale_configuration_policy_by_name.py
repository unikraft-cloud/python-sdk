from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_autoscale_configuration_policy_response import GetAutoscaleConfigurationPolicyResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
    name: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/v1/services/{uuid}/autoscale/policies/{name}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> GetAutoscaleConfigurationPolicyResponse:
    response_default = GetAutoscaleConfigurationPolicyResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetAutoscaleConfigurationPolicyResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    uuid: UUID,
    name: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[GetAutoscaleConfigurationPolicyResponse]:
    """Get Autoscale Configuration Policy by Name

     Return the current state and configuration of an autoscale policy given
    the service group UUID and the name of the policy.

    Args:
        uuid (UUID):
        name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAutoscaleConfigurationPolicyResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        name=name,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    uuid: UUID,
    name: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[GetAutoscaleConfigurationPolicyResponse]:
    """Get Autoscale Configuration Policy by Name

     Return the current state and configuration of an autoscale policy given
    the service group UUID and the name of the policy.

    Args:
        uuid (UUID):
        name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAutoscaleConfigurationPolicyResponse
    """

    return sync_detailed(
        uuid=uuid,
        name=name,
        client=client,
    ).parsed


async def asyncio_detailed(
    uuid: UUID,
    name: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[GetAutoscaleConfigurationPolicyResponse]:
    """Get Autoscale Configuration Policy by Name

     Return the current state and configuration of an autoscale policy given
    the service group UUID and the name of the policy.

    Args:
        uuid (UUID):
        name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetAutoscaleConfigurationPolicyResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        name=name,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    uuid: UUID,
    name: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[GetAutoscaleConfigurationPolicyResponse]:
    """Get Autoscale Configuration Policy by Name

     Return the current state and configuration of an autoscale policy given
    the service group UUID and the name of the policy.

    Args:
        uuid (UUID):
        name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetAutoscaleConfigurationPolicyResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            name=name,
            client=client,
        )
    ).parsed
