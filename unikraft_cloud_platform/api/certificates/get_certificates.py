from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_certificates_response import GetCertificatesResponse
from ...models.name_or_uuid import NameOrUUID
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: list["NameOrUUID"],
    details: Union[Unset, bool] = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["details"] = details

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/certificates",
        "params": params,
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item = body_item_data.to_dict()
        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> GetCertificatesResponse:
    response_default = GetCertificatesResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetCertificatesResponse]:
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
    details: Union[Unset, bool] = UNSET,
) -> Response[GetCertificatesResponse]:
    """List Certificates

     Get one or many certificates with their current status and configuration.
    It's possible to filter this list by name or UUID.

    Args:
        details (Union[Unset, bool]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetCertificatesResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        details=details,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
    details: Union[Unset, bool] = UNSET,
) -> Optional[GetCertificatesResponse]:
    """List Certificates

     Get one or many certificates with their current status and configuration.
    It's possible to filter this list by name or UUID.

    Args:
        details (Union[Unset, bool]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetCertificatesResponse
    """

    return sync_detailed(
        client=client,
        body=body,
        details=details,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
    details: Union[Unset, bool] = UNSET,
) -> Response[GetCertificatesResponse]:
    """List Certificates

     Get one or many certificates with their current status and configuration.
    It's possible to filter this list by name or UUID.

    Args:
        details (Union[Unset, bool]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetCertificatesResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        details=details,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: list["NameOrUUID"],
    details: Union[Unset, bool] = UNSET,
) -> Optional[GetCertificatesResponse]:
    """List Certificates

     Get one or many certificates with their current status and configuration.
    It's possible to filter this list by name or UUID.

    Args:
        details (Union[Unset, bool]):
        body (list['NameOrUUID']):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetCertificatesResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            details=details,
        )
    ).parsed
