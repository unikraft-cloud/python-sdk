from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.wait_instance_by_uuid_request_body import WaitInstanceByUUIDRequestBody
from ...models.wait_instance_response import WaitInstanceResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
    *,
    body: WaitInstanceByUUIDRequestBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/v1/instances/{uuid}/wait",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> WaitInstanceResponse:
    response_default = WaitInstanceResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[WaitInstanceResponse]:
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
    body: WaitInstanceByUUIDRequestBody,
) -> Response[WaitInstanceResponse]:
    """Wait for Instance State by UUID

     Wait for an instance to reach a certain state, by its UUID.

    If the instance is already in the desired state, the request will return
    immediately.  If the instance is not in the desired state, the request will
    block until the instance reaches the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instance reaches the desired state.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (WaitInstanceByUUIDRequestBody): Wait parameters.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[WaitInstanceResponse]
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
    body: WaitInstanceByUUIDRequestBody,
) -> Optional[WaitInstanceResponse]:
    """Wait for Instance State by UUID

     Wait for an instance to reach a certain state, by its UUID.

    If the instance is already in the desired state, the request will return
    immediately.  If the instance is not in the desired state, the request will
    block until the instance reaches the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instance reaches the desired state.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (WaitInstanceByUUIDRequestBody): Wait parameters.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        WaitInstanceResponse
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
    body: WaitInstanceByUUIDRequestBody,
) -> Response[WaitInstanceResponse]:
    """Wait for Instance State by UUID

     Wait for an instance to reach a certain state, by its UUID.

    If the instance is already in the desired state, the request will return
    immediately.  If the instance is not in the desired state, the request will
    block until the instance reaches the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instance reaches the desired state.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (WaitInstanceByUUIDRequestBody): Wait parameters.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[WaitInstanceResponse]
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
    body: WaitInstanceByUUIDRequestBody,
) -> Optional[WaitInstanceResponse]:
    """Wait for Instance State by UUID

     Wait for an instance to reach a certain state, by its UUID.

    If the instance is already in the desired state, the request will return
    immediately.  If the instance is not in the desired state, the request will
    block until the instance reaches the desired state or the timeout is
    reached.  If the timeout is reached, the request will fail with an error.
    If the timeout is -1, the request will block indefinitely until the
    instance reaches the desired state.

    Args:
        uuid (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
        body (WaitInstanceByUUIDRequestBody): Wait parameters.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        WaitInstanceResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            body=body,
        )
    ).parsed
