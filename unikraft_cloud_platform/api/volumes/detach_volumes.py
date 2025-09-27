from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.detach_volumes_request import DetachVolumesRequest
from ...models.detach_volumes_response import DetachVolumesResponse
from ...types import Response


def _get_kwargs(
    *,
    body: DetachVolumesRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/v1/volumes/detach",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> DetachVolumesResponse:
    response_default = DetachVolumesResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[DetachVolumesResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: DetachVolumesRequest,
) -> Response[DetachVolumesResponse]:
    """Detach Volumes

     Detach volumes specified by ID(s) (name or UUID) from instances.  If no
    particular instance is specified the volume is detached from all instances.
    The instances from which to detach must not have the volumes mounted.  The
    API returns an error for each instance from which it was unable to detach
    the volume.  If the volume has been created together with an instance,
    detaching the volume will make it persistent (i.e., it survives the
    deletion of the instance).

    Args:
        body (DetachVolumesRequest): The request message for detaching one or more volume(s) from
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DetachVolumesResponse]
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
    body: DetachVolumesRequest,
) -> Optional[DetachVolumesResponse]:
    """Detach Volumes

     Detach volumes specified by ID(s) (name or UUID) from instances.  If no
    particular instance is specified the volume is detached from all instances.
    The instances from which to detach must not have the volumes mounted.  The
    API returns an error for each instance from which it was unable to detach
    the volume.  If the volume has been created together with an instance,
    detaching the volume will make it persistent (i.e., it survives the
    deletion of the instance).

    Args:
        body (DetachVolumesRequest): The request message for detaching one or more volume(s) from
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DetachVolumesResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: DetachVolumesRequest,
) -> Response[DetachVolumesResponse]:
    """Detach Volumes

     Detach volumes specified by ID(s) (name or UUID) from instances.  If no
    particular instance is specified the volume is detached from all instances.
    The instances from which to detach must not have the volumes mounted.  The
    API returns an error for each instance from which it was unable to detach
    the volume.  If the volume has been created together with an instance,
    detaching the volume will make it persistent (i.e., it survives the
    deletion of the instance).

    Args:
        body (DetachVolumesRequest): The request message for detaching one or more volume(s) from
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DetachVolumesResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: DetachVolumesRequest,
) -> Optional[DetachVolumesResponse]:
    """Detach Volumes

     Detach volumes specified by ID(s) (name or UUID) from instances.  If no
    particular instance is specified the volume is detached from all instances.
    The instances from which to detach must not have the volumes mounted.  The
    API returns an error for each instance from which it was unable to detach
    the volume.  If the volume has been created together with an instance,
    detaching the volume will make it persistent (i.e., it survives the
    deletion of the instance).

    Args:
        body (DetachVolumesRequest): The request message for detaching one or more volume(s) from
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DetachVolumesResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
