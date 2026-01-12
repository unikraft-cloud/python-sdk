from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ...client import AuthenticatedClient, Client
from ...models.attach_volume_by_uuid_request_body import AttachVolumeByUUIDRequestBody
from ...models.attach_volumes_response import AttachVolumesResponse
from ...types import Response


def _get_kwargs(
    uuid: UUID,
    *,
    body: AttachVolumeByUUIDRequestBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": f"/v1/volumes/{uuid}/attach",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> AttachVolumesResponse:
    response_default = AttachVolumesResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[AttachVolumesResponse]:
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
    body: AttachVolumeByUUIDRequestBody,
) -> Response[AttachVolumesResponse]:
    """Attach Volume by UUID

     Attach a volume by UUID to an instance so that the volume is mounted when
    the instance starts.  The volume needs to be in `available` state and the
    instance must be in `stopped` state.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (AttachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AttachVolumesResponse]
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
    body: AttachVolumeByUUIDRequestBody,
) -> Optional[AttachVolumesResponse]:
    """Attach Volume by UUID

     Attach a volume by UUID to an instance so that the volume is mounted when
    the instance starts.  The volume needs to be in `available` state and the
    instance must be in `stopped` state.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (AttachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AttachVolumesResponse
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
    body: AttachVolumeByUUIDRequestBody,
) -> Response[AttachVolumesResponse]:
    """Attach Volume by UUID

     Attach a volume by UUID to an instance so that the volume is mounted when
    the instance starts.  The volume needs to be in `available` state and the
    instance must be in `stopped` state.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (AttachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AttachVolumesResponse]
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
    body: AttachVolumeByUUIDRequestBody,
) -> Optional[AttachVolumesResponse]:
    """Attach Volume by UUID

     Attach a volume by UUID to an instance so that the volume is mounted when
    the instance starts.  The volume needs to be in `available` state and the
    instance must be in `stopped` state.

    Args:
        uuid (UUID):  Example: c1d2e3f4-5678-90ab-cdef-1234567890ab.
        body (AttachVolumeByUUIDRequestBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AttachVolumesResponse
    """

    return (
        await asyncio_detailed(
            uuid=uuid,
            client=client,
            body=body,
        )
    ).parsed
