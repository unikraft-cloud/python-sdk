from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.update_instance_by_uuid_request_body import UpdateInstanceByUUIDRequestBody
from ...models.update_instances_response import UpdateInstancesResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
    *,
    body: UpdateInstanceByUUIDRequestBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": f"/v1/instances/{uuid}",
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
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: UpdateInstanceByUUIDRequestBody,
) -> Response[UpdateInstancesResponse]:
    """Update Instance by UUID

     Update (modify) an instance by its UUID.  The instance must be in a stopped
    state for most update operations.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (UpdateInstanceByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UpdateInstancesResponse]
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
    body: UpdateInstanceByUUIDRequestBody,
) -> Optional[UpdateInstancesResponse]:
    """Update Instance by UUID

     Update (modify) an instance by its UUID.  The instance must be in a stopped
    state for most update operations.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (UpdateInstanceByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UpdateInstancesResponse
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
    body: UpdateInstanceByUUIDRequestBody,
) -> Response[UpdateInstancesResponse]:
    """Update Instance by UUID

     Update (modify) an instance by its UUID.  The instance must be in a stopped
    state for most update operations.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (UpdateInstanceByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UpdateInstancesResponse]
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
    body: UpdateInstanceByUUIDRequestBody,
) -> Optional[UpdateInstancesResponse]:
    """Update Instance by UUID

     Update (modify) an instance by its UUID.  The instance must be in a stopped
    state for most update operations.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (UpdateInstanceByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UpdateInstancesResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            body=body,
        )
    ).parsed
