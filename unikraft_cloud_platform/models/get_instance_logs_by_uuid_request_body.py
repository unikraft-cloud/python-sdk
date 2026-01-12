from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetInstanceLogsByUUIDRequestBody")


@_attrs_define
class GetInstanceLogsByUUIDRequestBody:
    offset: Union[Unset, int] = UNSET
    """ The byte offset of the log output to receive.  A negative sign makes the
    offset relative to the end of the log. """
    limit: Union[Unset, int] = UNSET
    """ The amount of bytes to return at most. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        offset = self.offset

        limit = self.limit

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if offset is not UNSET:
            field_dict["offset"] = offset
        if limit is not UNSET:
            field_dict["limit"] = limit

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        offset = d.pop("offset", UNSET)

        limit = d.pop("limit", UNSET)

        get_instance_logs_by_uuid_request_body = cls(
            offset=offset,
            limit=limit,
        )

        get_instance_logs_by_uuid_request_body.additional_properties = d
        return get_instance_logs_by_uuid_request_body

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
