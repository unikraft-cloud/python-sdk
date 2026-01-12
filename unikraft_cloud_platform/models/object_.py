from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Object")


@_attrs_define
class Object:
    """An object is a single component of an image which is external and can be
    uniquely identified by its digest.

    """

    digest: Union[Unset, str] = UNSET
    """ The digest is a string representation including the hashing
    algorithm and the hash value separated by a colon. """
    media_type: Union[Unset, str] = UNSET
    """ The media type of the layer is a string that identifies the type of
    content that the layer contains. """
    size: Union[Unset, int] = UNSET
    """ The size of the layer in bytes. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        digest = self.digest

        media_type = self.media_type

        size = self.size

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if digest is not UNSET:
            field_dict["digest"] = digest
        if media_type is not UNSET:
            field_dict["media_type"] = media_type
        if size is not UNSET:
            field_dict["size"] = size

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        digest = d.pop("digest", UNSET)

        media_type = d.pop("media_type", UNSET)

        size = d.pop("size", UNSET)

        object_ = cls(
            digest=digest,
            media_type=media_type,
            size=size,
        )

        object_.additional_properties = d
        return object_

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
