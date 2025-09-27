from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.body_instance_id import BodyInstanceID


T = TypeVar("T", bound="AttachVolumeByUUIDRequestBody")


@_attrs_define
class AttachVolumeByUUIDRequestBody:
    attach_to: "BodyInstanceID"
    """ Reference to the instance to detach the volume from. """
    at: str
    """ Path of the mountpoint.

    The path must be absolute, not contain `.` and `..` components, and not
    contain colons (`:`). The path must point to an empty directory. If the
    directory does not exist, it is created. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        attach_to = self.attach_to.to_dict()

        at = self.at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "attach_to": attach_to,
                "at": at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.body_instance_id import BodyInstanceID

        d = dict(src_dict)
        attach_to = BodyInstanceID.from_dict(d.pop("attach_to"))

        at = d.pop("at")

        attach_volume_by_uuid_request_body = cls(
            attach_to=attach_to,
            at=at,
        )

        attach_volume_by_uuid_request_body.additional_properties = d
        return attach_volume_by_uuid_request_body

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
