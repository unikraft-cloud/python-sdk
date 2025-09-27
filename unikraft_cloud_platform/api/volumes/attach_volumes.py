from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.attach_volumes_request import AttachVolumesRequest
from ...models.attach_volumes_response import AttachVolumesResponse
from ...types import Response


def _get_kwargs(
    *,
    body: AttachVolumesRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/v1/volumes/attach",
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
    *,
    client: Union[AuthenticatedClient, Client],
    body: AttachVolumesRequest,
) -> Response[AttachVolumesResponse]:
    """Attach Volumes

     Attach one or more volumes specified by ID(s) (name or UUID) to instances
    so that the volumes are mounted when the instances start.  The volumes need
    to be in `available` state and the instances must be in `stopped` state.

    Args:
        body (AttachVolumesRequest): The request message for attaching one or more volume(s) to
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AttachVolumesResponse]
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
    body: AttachVolumesRequest,
) -> Optional[AttachVolumesResponse]:
    """Attach Volumes

     Attach one or more volumes specified by ID(s) (name or UUID) to instances
    so that the volumes are mounted when the instances start.  The volumes need
    to be in `available` state and the instances must be in `stopped` state.

    Args:
        body (AttachVolumesRequest): The request message for attaching one or more volume(s) to
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AttachVolumesResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: AttachVolumesRequest,
) -> Response[AttachVolumesResponse]:
    """Attach Volumes

     Attach one or more volumes specified by ID(s) (name or UUID) to instances
    so that the volumes are mounted when the instances start.  The volumes need
    to be in `available` state and the instances must be in `stopped` state.

    Args:
        body (AttachVolumesRequest): The request message for attaching one or more volume(s) to
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AttachVolumesResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: AttachVolumesRequest,
) -> Optional[AttachVolumesResponse]:
    """Attach Volumes

     Attach one or more volumes specified by ID(s) (name or UUID) to instances
    so that the volumes are mounted when the instances start.  The volumes need
    to be in `available` state and the instances must be in `stopped` state.

    Args:
        body (AttachVolumesRequest): The request message for attaching one or more volume(s) to
            instances by
            their UUID(s) or name(s).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AttachVolumesResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
