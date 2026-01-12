from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ServiceGroupInstance")


@_attrs_define
class ServiceGroupInstance:
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the instance.  This is a unique identifier for the instance
    that is generated when the instance is created.  The UUID is used to
    reference the instance in API calls and can be used to identify the
    instance in all API calls that require an instance identifier. """
    name: Union[Unset, str] = UNSET
    """ The name of the instance.  This is a human-readable name that can be used
    to identify the instance.  The name must be unique within the context of
    your account.  If no name is specified, a random name is generated for
    you.  The name can also be used to identify the instance in API calls. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        service_group_instance = cls(
            uuid=uuid,
            name=name,
        )

        service_group_instance.additional_properties = d
        return service_group_instance

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
