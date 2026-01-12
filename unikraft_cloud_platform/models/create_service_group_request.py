from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_service_group_request_domain import CreateServiceGroupRequestDomain
    from ..models.service import Service


T = TypeVar("T", bound="CreateServiceGroupRequest")


@_attrs_define
class CreateServiceGroupRequest:
    """The request message for creating a new service group."""

    name: Union[Unset, str] = UNSET
    """ Name of the service group.  This is a human-readable name that can be used
    to identify the service group.  The name must be unique within the context
    of your account.  If no name is specified, a random name is generated for
    you.  The name can also be used to identify the service group in API calls. """
    services: Union[Unset, list["Service"]] = UNSET
    """ Description of exposed services. """
    domains: Union[Unset, list["CreateServiceGroupRequestDomain"]] = UNSET
    """ Description of domains associated with the service group. """
    soft_limit: Union[Unset, int] = UNSET
    """ The soft limit is used by the Unikraft Cloud load balancer to decide when
    to wake up another standby instance.

    For example, if the soft limit is set to 5 and the service consists of 2
    standby instances, one of the instances receives up to 5 concurrent
    requests.  The 6th parallel requests wakes up the second instance.  If
    there are no more standby instances to wake up, the number of requests
    assigned to each instance will exceed the soft limit.  The load balancer
    makes sure that when the number of in-flight requests goes down again,
    instances are put into standby as fast as possible. """
    hard_limit: Union[Unset, int] = UNSET
    """ The hard limit defines the maximum number of concurrent requests that an
    instance assigned to the this service can handle.

    The load balancer will never assign more requests to a single instance.  In
    case there are no other instances available, excess requests fail (i.e.,
    they are blocked and not queued). """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        services: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.services, Unset):
            services = []
            for services_item_data in self.services:
                services_item = services_item_data.to_dict()
                services.append(services_item)

        domains: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.domains, Unset):
            domains = []
            for domains_item_data in self.domains:
                domains_item = domains_item_data.to_dict()
                domains.append(domains_item)

        soft_limit = self.soft_limit

        hard_limit = self.hard_limit

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if services is not UNSET:
            field_dict["services"] = services
        if domains is not UNSET:
            field_dict["domains"] = domains
        if soft_limit is not UNSET:
            field_dict["soft_limit"] = soft_limit
        if hard_limit is not UNSET:
            field_dict["hard_limit"] = hard_limit

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_service_group_request_domain import CreateServiceGroupRequestDomain
        from ..models.service import Service

        d = dict(src_dict)
        name = d.pop("name", UNSET)

        services = []
        _services = d.pop("services", UNSET)
        for services_item_data in _services or []:
            services_item = Service.from_dict(services_item_data)

            services.append(services_item)

        domains = []
        _domains = d.pop("domains", UNSET)
        for domains_item_data in _domains or []:
            domains_item = CreateServiceGroupRequestDomain.from_dict(domains_item_data)

            domains.append(domains_item)

        soft_limit = d.pop("soft_limit", UNSET)

        hard_limit = d.pop("hard_limit", UNSET)

        create_service_group_request = cls(
            name=name,
            services=services,
            domains=domains,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
        )

        create_service_group_request.additional_properties = d
        return create_service_group_request

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
