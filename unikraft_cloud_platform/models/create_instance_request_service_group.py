from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_instance_request_domain import CreateInstanceRequestDomain
    from ..models.service import Service


T = TypeVar("T", bound="CreateInstanceRequestServiceGroup")


@_attrs_define
class CreateInstanceRequestServiceGroup:
    """The service group configuration when creating an instance.

    If no existing (persistent) service group is specified via its identifier,
    a new (ephemeral) service group can be created by specifying the services
    it should expose.  A service defines the configuration settings of an
    exposed port by the instance.  A service is a combination of a public port,
    an internal port, and a set of handlers that define how the service will
    handle incoming connections.

    """

    domains: Union[Unset, list["CreateInstanceRequestDomain"]] = UNSET
    """ Similarly, if no existing (persistent) service group is specified via its
    identifier, a new (ephemeral) service group can be created.  In addition
    to the services it must expose, you can specify which domains it should
    use too. """
    services: Union[Unset, list["Service"]] = UNSET
    """ If no existing service identifier is provided, one or more new
    (ephemeral, non-persistent) service(s) can be created with the following
    definitions. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        domains: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.domains, Unset):
            domains = []
            for domains_item_data in self.domains:
                domains_item = domains_item_data.to_dict()
                domains.append(domains_item)

        services: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.services, Unset):
            services = []
            for services_item_data in self.services:
                services_item = services_item_data.to_dict()
                services.append(services_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if domains is not UNSET:
            field_dict["domains"] = domains
        if services is not UNSET:
            field_dict["services"] = services

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_instance_request_domain import CreateInstanceRequestDomain
        from ..models.service import Service

        d = dict(src_dict)
        domains = []
        _domains = d.pop("domains", UNSET)
        for domains_item_data in _domains or []:
            domains_item = CreateInstanceRequestDomain.from_dict(domains_item_data)

            domains.append(domains_item)

        services = []
        _services = d.pop("services", UNSET)
        for services_item_data in _services or []:
            services_item = Service.from_dict(services_item_data)

            services.append(services_item)

        create_instance_request_service_group = cls(
            domains=domains,
            services=services,
        )

        create_instance_request_service_group.additional_properties = d
        return create_instance_request_service_group

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
