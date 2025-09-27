from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.body_instance_id import BodyInstanceID


T = TypeVar("T", bound="DetachVolumeByUUIDRequestBody")


@_attrs_define
class DetachVolumeByUUIDRequestBody:
    from_: Union[Unset, "BodyInstanceID"] = UNSET
    """ Reference to the instance to detach the volume from. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from_: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.from_, Unset):
            from_ = self.from_.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if from_ is not UNSET:
            field_dict["from"] = from_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.body_instance_id import BodyInstanceID

        d = dict(src_dict)
        _from_ = d.pop("from", UNSET)
        from_: Union[Unset, BodyInstanceID]
        if isinstance(_from_, Unset):
            from_ = UNSET
        else:
            from_ = BodyInstanceID.from_dict(_from_)

        detach_volume_by_uuid_request_body = cls(
            from_=from_,
        )

        detach_volume_by_uuid_request_body.additional_properties = d
        return detach_volume_by_uuid_request_body

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
