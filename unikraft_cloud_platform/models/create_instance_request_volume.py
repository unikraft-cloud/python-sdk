from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateInstanceRequestVolume")


@_attrs_define
class CreateInstanceRequestVolume:
    """A volume defines a storage volume that can be attached to the instance."""

    at: str
    """ The mount point for the volume in the instance. """
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of an existing volume.

    If this is the only specified field, then it will look up an existing
    volume by this UUID. """
    name: Union[Unset, str] = UNSET
    """ The name of the volume.

    If this is the only specified field, then it will look up an existing
    volume by this name.  If the volume does not exist, the request will
    fail.  If a new volume is intended to be created, then this field must be
    specified along with the size in MiB and the mount point in the instance. """
    size_mb: Union[Unset, int] = UNSET
    """ The size of the volume when creating a new volume.

    When creating a new volume as part of the instance create request,
    specify the size of the volume in MiB. """
    read_only: Union[Unset, bool] = UNSET
    """ Whether the volume is read-only.

    If this field is set to true, the volume will be mounted as read-only in
    the instance.  This field is optional and defaults to false and is only
    applicable when using an existing volume. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        at = self.at

        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        size_mb = self.size_mb

        read_only = self.read_only

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "at": at,
            }
        )
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if size_mb is not UNSET:
            field_dict["size_mb"] = size_mb
        if read_only is not UNSET:
            field_dict["read_only"] = read_only

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        at = d.pop("at")

        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        size_mb = d.pop("size_mb", UNSET)

        read_only = d.pop("read_only", UNSET)

        create_instance_request_volume = cls(
            at=at,
            uuid=uuid,
            name=name,
            size_mb=size_mb,
            read_only=read_only,
        )

        create_instance_request_volume.additional_properties = d
        return create_instance_request_volume

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
