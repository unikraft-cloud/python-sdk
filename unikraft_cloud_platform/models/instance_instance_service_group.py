from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.instance_service_group_instance_domain import InstanceServiceGroupInstanceDomain


T = TypeVar("T", bound="InstanceInstanceServiceGroup")


@_attrs_define
class InstanceInstanceServiceGroup:
    """The service group configuration for the instance.

    This is a reference to the service group that the instance is part of.  The
    service group defines the services (e.g. ports, connection handling) that
    the instance exposes and how they are configured.

    """

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the service group.

    This is a unique identifier for the service group that is generated when
    the service is created.  The UUID is used to reference the service group
    in API calls and can be used to identify the service in all API calls
    that require an service identifier. """
    name: Union[Unset, str] = UNSET
    """ The name of the service group.

    This is a human-readable name that can be used to identify the service
    group.  The name is unique within the context of your account.  The name
    can also be used to identify the service group in API calls. """
    domains: Union[Unset, list["InstanceServiceGroupInstanceDomain"]] = UNSET
    """ The domain configuration for the service group. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        domains: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.domains, Unset):
            domains = []
            for domains_item_data in self.domains:
                domains_item = domains_item_data.to_dict()
                domains.append(domains_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if domains is not UNSET:
            field_dict["domains"] = domains

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.instance_service_group_instance_domain import InstanceServiceGroupInstanceDomain

        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        domains = []
        _domains = d.pop("domains", UNSET)
        for domains_item_data in _domains or []:
            domains_item = InstanceServiceGroupInstanceDomain.from_dict(domains_item_data)

            domains.append(domains_item)

        instance_instance_service_group = cls(
            uuid=uuid,
            name=name,
            domains=domains,
        )

        instance_instance_service_group.additional_properties = d
        return instance_instance_service_group

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
