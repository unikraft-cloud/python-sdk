from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_instance_logs_by_uuid_request_body import GetInstanceLogsByUUIDRequestBody
from ...models.get_instance_logs_response import GetInstanceLogsResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
    *,
    body: GetInstanceLogsByUUIDRequestBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/v1/instances/{uuid}/log",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> GetInstanceLogsResponse:
    response_default = GetInstanceLogsResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetInstanceLogsResponse]:
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
    body: GetInstanceLogsByUUIDRequestBody,
) -> Response[GetInstanceLogsResponse]:
    """Get Instance Logs by UUID

     Retrieve the logs of an instance by its UUID.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (GetInstanceLogsByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstanceLogsResponse]
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
    body: GetInstanceLogsByUUIDRequestBody,
) -> Optional[GetInstanceLogsResponse]:
    """Get Instance Logs by UUID

     Retrieve the logs of an instance by its UUID.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (GetInstanceLogsByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstanceLogsResponse
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
    body: GetInstanceLogsByUUIDRequestBody,
) -> Response[GetInstanceLogsResponse]:
    """Get Instance Logs by UUID

     Retrieve the logs of an instance by its UUID.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (GetInstanceLogsByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstanceLogsResponse]
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
    body: GetInstanceLogsByUUIDRequestBody,
) -> Optional[GetInstanceLogsResponse]:
    """Get Instance Logs by UUID

     Retrieve the logs of an instance by its UUID.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (GetInstanceLogsByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstanceLogsResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            body=body,
        )
    ).parsed
