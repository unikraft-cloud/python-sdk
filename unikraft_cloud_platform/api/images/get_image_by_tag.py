from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_image_response import GetImageResponse
from ...types import Response


def _get_kwargs(
    tag: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/v1/images/tag/{tag}",
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
    tag: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[GetImageResponse]:
    """Get Image by Tag

     Retrieve an image by its tag.

    Args:
        tag (str):  Example: my-image:latest.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetImageResponse]
    """

    kwargs = _get_kwargs(
        tag=tag,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tag: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[GetImageResponse]:
    """Get Image by Tag

     Retrieve an image by its tag.

    Args:
        tag (str):  Example: my-image:latest.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetImageResponse
    """

    return sync_detailed(
        tag=tag,
        client=client,
    ).parsed


async def asyncio_detailed(
    tag: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[GetImageResponse]:
    """Get Image by Tag

     Retrieve an image by its tag.

    Args:
        tag (str):  Example: my-image:latest.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetImageResponse]
    """

    kwargs = _get_kwargs(
        tag=tag,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tag: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[GetImageResponse]:
    """Get Image by Tag

     Retrieve an image by its tag.

    Args:
        tag (str):  Example: my-image:latest.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetImageResponse
    """

    return (
        await asyncio_detailed(
            tag=tag,
            client=client,
        )
    ).parsed
