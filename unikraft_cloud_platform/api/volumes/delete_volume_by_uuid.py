from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.delete_volumes_response import DeleteVolumesResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/v1/volumes/{uuid}",
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> DeleteVolumesResponse:
    response_default = DeleteVolumesResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[DeleteVolumesResponse]:
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
) -> Response[DeleteVolumesResponse]:
    """Delete Volume by UUID

     Delete the specified volume by its UUID.  If the volume is still attached
    to an instance, the operation fails.  After this call, the IDs associated
    with the volume are no longer valid.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteVolumesResponse]
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
) -> Optional[DeleteVolumesResponse]:
    """Delete Volume by UUID

     Delete the specified volume by its UUID.  If the volume is still attached
    to an instance, the operation fails.  After this call, the IDs associated
    with the volume are no longer valid.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteVolumesResponse
    """

    return sync_detailed(
        uuid=uuid,
        client=client,
    ).parsed


async def asyncio_detailed(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[DeleteVolumesResponse]:
    """Delete Volume by UUID

     Delete the specified volume by its UUID.  If the volume is still attached
    to an instance, the operation fails.  After this call, the IDs associated
    with the volume are no longer valid.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteVolumesResponse]
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
) -> Optional[DeleteVolumesResponse]:
    """Delete Volume by UUID

     Delete the specified volume by its UUID.  If the volume is still attached
    to an instance, the operation fails.  After this call, the IDs associated
    with the volume are no longer valid.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteVolumesResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
        )
    ).parsed
