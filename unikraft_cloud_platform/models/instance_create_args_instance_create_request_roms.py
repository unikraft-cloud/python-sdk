from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="InstanceCreateArgsInstanceCreateRequestRoms")


@_attrs_define
class InstanceCreateArgsInstanceCreateRequestRoms:
    image: str
    """ The image of the ROM to use for the autoscale configuration. """
    name: Union[Unset, str] = UNSET
    """ The name of the ROM to use for the autoscale configuration. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        image = self.image

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "image": image,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        image = d.pop("image")

        name = d.pop("name", UNSET)

        instance_create_args_instance_create_request_roms = cls(
            image=image,
            name=name,
        )

        instance_create_args_instance_create_request_roms.additional_properties = d
        return instance_create_args_instance_create_request_roms

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
