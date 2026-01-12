import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.domain import Domain
    from ..models.service import Service
    from ..models.service_group_instance import ServiceGroupInstance


T = TypeVar("T", bound="ServiceGroup")


@_attrs_define
class ServiceGroup:
    """A service group on Unikraft Cloud is used to describe how your application
    exposes its functionality to the outside world.  Once defined, assigning an
    instance to the service will make it accessible from the Internet.

    An application, running as an instance, may expose one or more ports, e.g. it
    listens on port 80 because your application exposes a HTTP web service. This,
    along with a set of additional metadata defines how the "service" is
    configured and accessed.  For example, a service may be configured to use
    TLS, or be bound to a specific domain name.

    When an instance is assigned to a service group, it immediately becomes
    accessible over the Internet on the exposed public port, using the set DNS
    name, and is routed to the set destination port.

    Note: If you do not specify a DNS name when you create a service and you
    indicate that the application exposes some ports, Unikraft Cloud will
    generates a random DNS name for you.  Unikraft Cloud also supports custom
    domains like www.example.com and wildcard domains like *.example.com.

    """

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the service group.

    This is a unique identifier for the service group that is generated when
    the service group is created.  The UUID is used to reference the service in
    API calls and can be used to identify the service group in all API calls
    that require an identifier. """
    name: Union[Unset, str] = UNSET
    """ The name of the service group.

    This is a human-readable name that can be used to identify the service
    group. The name must be unique within the context of your account.  The
    name can also be used to identify the service in API calls. """
    created_at: Union[Unset, datetime.datetime] = UNSET
    """ The time the service was created. """
    persistent: Union[Unset, bool] = UNSET
    """ Indicates if the service will stay remain even after the last instance
    detached.  If this is set to false, the service will be deleted when the
    last instance detached from it.  If this is set to true, the service will
    remain and can be reused by other instances.  This is useful if you want to
    keep the service configuration, e.g., the published ports, handlers, and
    domains, even if there are no instances assigned to it. """
    autoscale: Union[Unset, bool] = UNSET
    """ Indicates if the service has autoscale enabled.  See the associated
    autoscale documentation for more information about how to set this up.
    Autoscale policies can be set up after the service has been created. """
    soft_limit: Union[Unset, int] = UNSET
    """ The soft limit is used by the Unikraft Cloud load balancer to decide when
    to wake up another standby instance.  For example, if the soft limit is set
    to 5 and the service consists of 2 standby instances, one of the instances
    receives up to 5 concurrent requests.  The 6th parallel requests wakes up
    the second instance.  If there are no more standby instances to wake up,
    the number of requests assigned to each instance will exceed the soft
    limit.  The load balancer makes sure that when the number of in-flight
    requests goes down again, instances are put into standby as fast as
    possible. """
    hard_limit: Union[Unset, int] = UNSET
    """ The hard limit defines the maximum number of concurrent requests that an
    instance assigned to the this service can handle.  The load balancer will
    never assign more requests to a single instance.  In case there are no
    other instances available, excess requests fail (i.e., they are blocked and
    not queued). """
    services: Union[Unset, list["Service"]] = UNSET
    """ List of published network ports for this service and the destination port
    to which Unikraft Cloud will forward traffic to.  Additional handlers can
    be defined for each published port in order to define how the service will
    handle incoming connections and forward traffic from the Internet to your
    application.  For example, a service can be configured to terminate TLS
    connections, redirect HTTP traffic, or enable HTTP mode for load balancing. """
    domains: Union[Unset, list["Domain"]] = UNSET
    """ List of domains associated with the service.  Domains are used to access
    the service over the Internet. """
    instances: Union[Unset, list["ServiceGroupInstance"]] = UNSET
    """ List of instances assigned to the service. """
    status: Union[Unset, ResponseStatus] = UNSET
    """ The response status of an API request. """
    message: Union[Unset, str] = UNSET
    """ An optional message providing additional information about the status.
    This field is only set when this message object is used as a response
    message, and is useful when the status is not `success`. """
    error: Union[Unset, int] = UNSET
    """ An optional error code providing additional information about the status.
    This field is only set when this message object is used as a response
    message, and is useful when the status is not `success`. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        created_at: Union[Unset, str] = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        persistent = self.persistent

        autoscale = self.autoscale

        soft_limit = self.soft_limit

        hard_limit = self.hard_limit

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

        instances: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.instances, Unset):
            instances = []
            for instances_item_data in self.instances:
                instances_item = instances_item_data.to_dict()
                instances.append(instances_item)

        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if persistent is not UNSET:
            field_dict["persistent"] = persistent
        if autoscale is not UNSET:
            field_dict["autoscale"] = autoscale
        if soft_limit is not UNSET:
            field_dict["soft_limit"] = soft_limit
        if hard_limit is not UNSET:
            field_dict["hard_limit"] = hard_limit
        if services is not UNSET:
            field_dict["services"] = services
        if domains is not UNSET:
            field_dict["domains"] = domains
        if instances is not UNSET:
            field_dict["instances"] = instances
        if status is not UNSET:
            field_dict["status"] = status
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.domain import Domain
        from ..models.service import Service
        from ..models.service_group_instance import ServiceGroupInstance

        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        _created_at = d.pop("created_at", UNSET)
        created_at: Union[Unset, datetime.datetime]
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        persistent = d.pop("persistent", UNSET)

        autoscale = d.pop("autoscale", UNSET)

        soft_limit = d.pop("soft_limit", UNSET)

        hard_limit = d.pop("hard_limit", UNSET)

        services = []
        _services = d.pop("services", UNSET)
        for services_item_data in _services or []:
            services_item = Service.from_dict(services_item_data)

            services.append(services_item)

        domains = []
        _domains = d.pop("domains", UNSET)
        for domains_item_data in _domains or []:
            domains_item = Domain.from_dict(domains_item_data)

            domains.append(domains_item)

        instances = []
        _instances = d.pop("instances", UNSET)
        for instances_item_data in _instances or []:
            instances_item = ServiceGroupInstance.from_dict(instances_item_data)

            instances.append(instances_item)

        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        service_group = cls(
            uuid=uuid,
            name=name,
            created_at=created_at,
            persistent=persistent,
            autoscale=autoscale,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
            services=services,
            domains=domains,
            instances=instances,
            status=status,
            message=message,
            error=error,
        )

        service_group.additional_properties = d
        return service_group

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
