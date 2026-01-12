from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ...client import AuthenticatedClient, Client
from ...models.get_instance_metrics_response import GetInstanceMetricsResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    uuid: Union[Unset, str] = UNSET,
    name: Union[Unset, str] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["uuid"] = uuid

    params["name"] = name

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/instances/metrics",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> GetInstanceMetricsResponse:
    response_default = GetInstanceMetricsResponse.from_dict(response.json())

    return response_default


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[GetInstanceMetricsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    uuid: Union[Unset, str] = UNSET,
    name: Union[Unset, str] = UNSET,
) -> Response[GetInstanceMetricsResponse]:
    """Get Instances Metrics

     Get the metrics of an instance by its UUID or name.

    Args:
        uuid (Union[Unset, str]):
        name (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstanceMetricsResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        name=name,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    uuid: Union[Unset, str] = UNSET,
    name: Union[Unset, str] = UNSET,
) -> Optional[GetInstanceMetricsResponse]:
    """Get Instances Metrics

     Get the metrics of an instance by its UUID or name.

    Args:
        uuid (Union[Unset, str]):
        name (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstanceMetricsResponse
    """

    return sync_detailed(
        client=client,
        uuid=uuid,
        name=name,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    uuid: Union[Unset, str] = UNSET,
    name: Union[Unset, str] = UNSET,
) -> Response[GetInstanceMetricsResponse]:
    """Get Instances Metrics

     Get the metrics of an instance by its UUID or name.

    Args:
        uuid (Union[Unset, str]):
        name (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetInstanceMetricsResponse]
    """

    kwargs = _get_kwargs(
        uuid=uuid,
        name=name,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    uuid: Union[Unset, str] = UNSET,
    name: Union[Unset, str] = UNSET,
) -> Optional[GetInstanceMetricsResponse]:
    """Get Instances Metrics

     Get the metrics of an instance by its UUID or name.

    Args:
        uuid (Union[Unset, str]):
        name (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetInstanceMetricsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            uuid=uuid,
            name=name,
        )
    ).parsed
