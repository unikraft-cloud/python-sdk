from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_volumes_response import GetVolumesResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    uuid: UUID,
    *,
    details: Union[Unset, bool] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["details"] = details

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/v1/volumes/{uuid}",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> GetVolumesResponse:
    response_default = GetVolumesResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetVolumesResponse]:
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
    details: Union[Unset, bool] = UNSET,
) -> Response[GetVolumesResponse]:
    """Get Volume by UUID

     Return the current status and the configuration of a particular volume by
    its UUID.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetVolumesResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        details=details,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    details: Union[Unset, bool] = UNSET,
) -> Optional[GetVolumesResponse]:
    """Get Volume by UUID

     Return the current status and the configuration of a particular volume by
    its UUID.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetVolumesResponse
    """

    return sync_detailed(
        uuid=uuid,
        client=client,
        details=details,
    ).parsed


async def asyncio_detailed(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    details: Union[Unset, bool] = UNSET,
) -> Response[GetVolumesResponse]:
    """Get Volume by UUID

     Return the current status and the configuration of a particular volume by
    its UUID.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetVolumesResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        details=details,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    details: Union[Unset, bool] = UNSET,
) -> Optional[GetVolumesResponse]:
    """Get Volume by UUID

     Return the current status and the configuration of a particular volume by
    its UUID.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        details (Union[Unset, bool]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetVolumesResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            details=details,
        )
    ).parsed
