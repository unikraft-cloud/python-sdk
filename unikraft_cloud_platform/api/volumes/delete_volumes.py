from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.delete_volumes_response import DeleteVolumesResponse
from ...models.name_or_uuid import NameOrUUID
from ...types import Response


def _get_kwargs(
    *,
    body: list["NameOrUUID"],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/v1/volumes",
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item = body_item_data.to_dict()
        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
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
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
) -> Response[DeleteVolumesResponse]:
    """Delete Volumes

     Delete one or more volumes by their UUID(s) or name(s).  If the volumes are
    still attached to an instance, the operation fails.  After this call, the
    IDs associated with the volumes are no longer valid.

    Args:
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteVolumesResponse]
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
    body: list["NameOrUUID"],
) -> Optional[DeleteVolumesResponse]:
    """Delete Volumes

     Delete one or more volumes by their UUID(s) or name(s).  If the volumes are
    still attached to an instance, the operation fails.  After this call, the
    IDs associated with the volumes are no longer valid.

    Args:
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteVolumesResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
) -> Response[DeleteVolumesResponse]:
    """Delete Volumes

     Delete one or more volumes by their UUID(s) or name(s).  If the volumes are
    still attached to an instance, the operation fails.  After this call, the
    IDs associated with the volumes are no longer valid.

    Args:
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteVolumesResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
) -> Optional[DeleteVolumesResponse]:
    """Delete Volumes

     Delete one or more volumes by their UUID(s) or name(s).  If the volumes are
    still attached to an instance, the operation fails.  After this call, the
    IDs associated with the volumes are no longer valid.

    Args:
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteVolumesResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
