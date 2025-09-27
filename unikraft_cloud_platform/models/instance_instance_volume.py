from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="InstanceInstanceVolume")


@_attrs_define
class InstanceInstanceVolume:
    """A volume defines a storage which can be attached to the instance.

    Volumes can be used to store persistent data which should remain available
    even if the instance is stopped or restarted.

    """

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the volume.

    This is a unique identifier for the volume that is generated when the
    volume is created.  The UUID is used to reference the volume in API calls
    and can be used to identify the volume in all API calls that require a
    volume identifier. """
    name: Union[Unset, str] = UNSET
    """ The name of the volume.

    This is a human-readable name that can be used to identify the volume.
    The name must be unique within the context of your account.  The name can
    also be used to identify the volume in API calls. """
    at: Union[Unset, str] = UNSET
    """ The mount point of the volume in the instance.  This is the directory in
    the instance where the volume will be mounted. """
    read_only: Union[Unset, bool] = UNSET
    """ Whether the volume is read-only or not. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        at = self.at

        read_only = self.read_only

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if at is not UNSET:
            field_dict["at"] = at
        if read_only is not UNSET:
            field_dict["read_only"] = read_only

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

        at = d.pop("at", UNSET)

        read_only = d.pop("read_only", UNSET)

        instance_instance_volume = cls(
            uuid=uuid,
            name=name,
            at=at,
            read_only=read_only,
        )

        instance_instance_volume.additional_properties = d
        return instance_instance_volume

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
