from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_volume_request import CreateVolumeRequest
from ...models.create_volume_response import CreateVolumeResponse
from ...types import Response


def _get_kwargs(
    *,
    body: CreateVolumeRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/volumes",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> CreateVolumeResponse:
    response_default = CreateVolumeResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[CreateVolumeResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateVolumeRequest,
) -> Response[CreateVolumeResponse]:
    """Create Volume

     Create a volume given the specified configuration parameters.
    The volume is automatically initialized with an empty file system.
    After initialization, the volume is in the `available` state and can be
    attached to an instance with the `PUT /v1/volumes/attach` endpoint.
    Note that, the size of a volume cannot be changed after creation.

    Args:
        body (CreateVolumeRequest): The request message for creating a volume.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateVolumeResponse]
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
    body: CreateVolumeRequest,
) -> Optional[CreateVolumeResponse]:
    """Create Volume

     Create a volume given the specified configuration parameters.
    The volume is automatically initialized with an empty file system.
    After initialization, the volume is in the `available` state and can be
    attached to an instance with the `PUT /v1/volumes/attach` endpoint.
    Note that, the size of a volume cannot be changed after creation.

    Args:
        body (CreateVolumeRequest): The request message for creating a volume.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateVolumeResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateVolumeRequest,
) -> Response[CreateVolumeResponse]:
    """Create Volume

     Create a volume given the specified configuration parameters.
    The volume is automatically initialized with an empty file system.
    After initialization, the volume is in the `available` state and can be
    attached to an instance with the `PUT /v1/volumes/attach` endpoint.
    Note that, the size of a volume cannot be changed after creation.

    Args:
        body (CreateVolumeRequest): The request message for creating a volume.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateVolumeResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreateVolumeRequest,
) -> Optional[CreateVolumeResponse]:
    """Create Volume

     Create a volume given the specified configuration parameters.
    The volume is automatically initialized with an empty file system.
    After initialization, the volume is in the `available` state and can be
    attached to an instance with the `PUT /v1/volumes/attach` endpoint.
    Note that, the size of a volume cannot be changed after creation.

    Args:
        body (CreateVolumeRequest): The request message for creating a volume.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateVolumeResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
