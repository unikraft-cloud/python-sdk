from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_image_response import GetImageResponse
from ...types import Response


def _get_kwargs(
    digest: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/v1/images/digest/{digest}",
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> GetImageResponse:
    response_default = GetImageResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetImageResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    digest: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[GetImageResponse]:
    """Get Image by Digest

     Retrieve an image by its digest.

    Args:
        digest (str):  Example:
            sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetImageResponse]
    """

    kwargs = _get_kwargs(
        digest=digest,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    digest: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[GetImageResponse]:
    """Get Image by Digest

     Retrieve an image by its digest.

    Args:
        digest (str):  Example:
            sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetImageResponse
    """

    return sync_detailed(
        digest=digest,
        client=client,
    ).parsed


async def asyncio_detailed(
    digest: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[GetImageResponse]:
    """Get Image by Digest

     Retrieve an image by its digest.

    Args:
        digest (str):  Example:
            sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetImageResponse]
    """

    kwargs = _get_kwargs(
        digest=digest,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    digest: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[GetImageResponse]:
    """Get Image by Digest

     Retrieve an image by its digest.

    Args:
        digest (str):  Example:
            sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetImageResponse
    """

    return (
        await asyncio_detailed(
            digest=digest,
            client=client,
        )
    ).parsed
