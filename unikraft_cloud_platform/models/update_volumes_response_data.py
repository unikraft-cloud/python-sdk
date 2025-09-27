from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.update_volumes_response_updated_volume import UpdateVolumesResponseUpdatedVolume


T = TypeVar("T", bound="UpdateVolumesResponseData")


@_attrs_define
class UpdateVolumesResponseData:
    volumes: Union[Unset, list["UpdateVolumesResponseUpdatedVolume"]] = UNSET
    """ List of volumes that were processed during the update operation. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        volumes: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.volumes, Unset):
            volumes = []
            for volumes_item_data in self.volumes:
                volumes_item = volumes_item_data.to_dict()
                volumes.append(volumes_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if volumes is not UNSET:
            field_dict["volumes"] = volumes

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.update_volumes_response_updated_volume import UpdateVolumesResponseUpdatedVolume

        d = dict(src_dict)
        volumes = []
        _volumes = d.pop("volumes", UNSET)
        for volumes_item_data in _volumes or []:
            volumes_item = UpdateVolumesResponseUpdatedVolume.from_dict(volumes_item_data)

            volumes.append(volumes_item)

        update_volumes_response_data = cls(
            volumes=volumes,
        )

        update_volumes_response_data.additional_properties = d
        return update_volumes_response_data

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
