from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.service_handlers_item import ServiceHandlersItem, check_service_handlers_item
from ..types import UNSET, Unset

T = TypeVar("T", bound="Service")


@_attrs_define
class Service:
    """A service connects a public-facing port to an internal destination port on
    which an application instance listens on.  Additional handlers can be defined
    for each published port in order to define how the service will handle
    incoming connections and forward traffic from the Internet to your
    application.  For example, a service can be configured to terminate TLS
    connections, redirect HTTP traffic, or enable HTTP mode for load balancing.

    """

    port: int
    """ This is the public-facing port that the service will be accessible from
    on the Internet. """
    destination_port: Union[Unset, int] = UNSET
    """ The port number that the instance is listening on.  This is the internal
    port which Unikraft Cloud will forward traffic to. """
    handlers: Union[Unset, list[ServiceHandlersItem]] = UNSET
    """ Connection handlers to use for the service.  Handlers define how the
    service will handle incoming connections and forward traffic from the
    Internet to your application.  For example, a service can be configured
    to terminate TLS connections, redirect HTTP traffic, or enable HTTP mode
    for load balancing.  You configure the handlers for every published
    service port individually. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        port = self.port

        destination_port = self.destination_port

        handlers: Union[Unset, list[str]] = UNSET
        if not isinstance(self.handlers, Unset):
            handlers = []
            for handlers_item_data in self.handlers:
                handlers_item: str = handlers_item_data
                handlers.append(handlers_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "port": port,
            }
        )
        if destination_port is not UNSET:
            field_dict["destination_port"] = destination_port
        if handlers is not UNSET:
            field_dict["handlers"] = handlers

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        port = d.pop("port")

        destination_port = d.pop("destination_port", UNSET)

        handlers = []
        _handlers = d.pop("handlers", UNSET)
        for handlers_item_data in _handlers or []:
            handlers_item = check_service_handlers_item(handlers_item_data)

            handlers.append(handlers_item)

        service = cls(
            port=port,
            destination_port=destination_port,
            handlers=handlers,
        )

        service.additional_properties = d
        return service

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
