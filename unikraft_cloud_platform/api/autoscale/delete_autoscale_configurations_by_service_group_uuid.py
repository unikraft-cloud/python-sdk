from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.delete_autoscale_configurations_response import DeleteAutoscaleConfigurationsResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/v1/services/{uuid}/autoscale",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> DeleteAutoscaleConfigurationsResponse:
    response_default = DeleteAutoscaleConfigurationsResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[DeleteAutoscaleConfigurationsResponse]:
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
) -> Response[DeleteAutoscaleConfigurationsResponse]:
    """Delete Autoscale Configurations by Service Group UUID

     Delete the autoscale configuration for the service group given its UUID.

    Unikraft Cloud will immediately drain all connections from all instances
    that have been created by autoscale and delete the instances afterwards.
    The draining phase is allowed to take at most `cooldown_time_ms`
    milliseconds after which remaining connections are forcefully closed.  The
    master instance is never deleted.  However, deleting the autoscale
    configuration causes the master instance to start if it is stopped.

    Args:
        uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteAutoscaleConfigurationsResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[DeleteAutoscaleConfigurationsResponse]:
    """Delete Autoscale Configurations by Service Group UUID

     Delete the autoscale configuration for the service group given its UUID.

    Unikraft Cloud will immediately drain all connections from all instances
    that have been created by autoscale and delete the instances afterwards.
    The draining phase is allowed to take at most `cooldown_time_ms`
    milliseconds after which remaining connections are forcefully closed.  The
    master instance is never deleted.  However, deleting the autoscale
    configuration causes the master instance to start if it is stopped.

    Args:
        uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteAutoscaleConfigurationsResponse
    """

    return sync_detailed(
        uuid=uuid,
        client=client,
    ).parsed


async def asyncio_detailed(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[DeleteAutoscaleConfigurationsResponse]:
    """Delete Autoscale Configurations by Service Group UUID

     Delete the autoscale configuration for the service group given its UUID.

    Unikraft Cloud will immediately drain all connections from all instances
    that have been created by autoscale and delete the instances afterwards.
    The draining phase is allowed to take at most `cooldown_time_ms`
    milliseconds after which remaining connections are forcefully closed.  The
    master instance is never deleted.  However, deleting the autoscale
    configuration causes the master instance to start if it is stopped.

    Args:
        uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteAutoscaleConfigurationsResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[DeleteAutoscaleConfigurationsResponse]:
    """Delete Autoscale Configurations by Service Group UUID

     Delete the autoscale configuration for the service group given its UUID.

    Unikraft Cloud will immediately drain all connections from all instances
    that have been created by autoscale and delete the instances afterwards.
    The draining phase is allowed to take at most `cooldown_time_ms`
    milliseconds after which remaining connections are forcefully closed.  The
    master instance is never deleted.  However, deleting the autoscale
    configuration causes the master instance to start if it is stopped.

    Args:
        uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteAutoscaleConfigurationsResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
        )
    ).parsed
