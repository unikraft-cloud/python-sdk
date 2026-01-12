from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.detach_volume_by_uuid_request_body import DetachVolumeByUUIDRequestBody
from ...models.detach_volumes_response import DetachVolumesResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
    *,
    body: DetachVolumeByUUIDRequestBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": f"/v1/volumes/{uuid}/detach",
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
    uuid: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: DetachVolumeByUUIDRequestBody,
) -> Response[DetachVolumesResponse]:
    """Detach Volume by UUID

     Detaches a volume by UUID from instances.  If no particular instance is
    specified the volume is detached from all instances.  The instances from
    which to detach must not have the volume mounted.  The API returns an error
    for each instance from which it was unable to detach the volume.  If the
    volume has been created together with an instance, detaching the volume
    will make it persistent (i.e., it survives the deletion of the instance).

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (DetachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DetachVolumesResponse]
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
    body: DetachVolumeByUUIDRequestBody,
) -> Optional[DetachVolumesResponse]:
    """Detach Volume by UUID

     Detaches a volume by UUID from instances.  If no particular instance is
    specified the volume is detached from all instances.  The instances from
    which to detach must not have the volume mounted.  The API returns an error
    for each instance from which it was unable to detach the volume.  If the
    volume has been created together with an instance, detaching the volume
    will make it persistent (i.e., it survives the deletion of the instance).

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (DetachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DetachVolumesResponse
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
    body: DetachVolumeByUUIDRequestBody,
) -> Response[DetachVolumesResponse]:
    """Detach Volume by UUID

     Detaches a volume by UUID from instances.  If no particular instance is
    specified the volume is detached from all instances.  The instances from
    which to detach must not have the volume mounted.  The API returns an error
    for each instance from which it was unable to detach the volume.  If the
    volume has been created together with an instance, detaching the volume
    will make it persistent (i.e., it survives the deletion of the instance).

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (DetachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DetachVolumesResponse]
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
    body: DetachVolumeByUUIDRequestBody,
) -> Optional[DetachVolumesResponse]:
    """Detach Volume by UUID

     Detaches a volume by UUID from instances.  If no particular instance is
    specified the volume is detached from all instances.  The instances from
    which to detach must not have the volume mounted.  The API returns an error
    for each instance from which it was unable to detach the volume.  If the
    volume has been created together with an instance, detaching the volume
    will make it persistent (i.e., it survives the deletion of the instance).

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (DetachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DetachVolumesResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            body=body,
        )
    ).parsed
