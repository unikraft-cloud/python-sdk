from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetInstanceLogsRequest")


@_attrs_define
class GetInstanceLogsRequest:
    """The request message for getting the logs of an instance by their UUID or
    name.

    """

    uuid: UUID
    """ The UUID of the instance to retrieve logs for.  Mutually exclusive with
    name. """
    name: str
    """ The name of the instance to retrieve logs for.  Mutually exclusive with
    UUID. """
    offset: Union[Unset, int] = UNSET
    """ The byte offset of the log output to receive.  A negative sign makes the
    offset relative to the end of the log. """
    limit: Union[Unset, int] = UNSET
    """ The amount of bytes to return at most. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid = str(self.uuid)

        name = self.name

        offset = self.offset

        limit = self.limit

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "uuid": uuid,
                "name": name,
            }
        )
        if offset is not UNSET:
            field_dict["offset"] = offset
        if limit is not UNSET:
            field_dict["limit"] = limit

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        uuid = UUID(d.pop("uuid"))

        name = d.pop("name")

        offset = d.pop("offset", UNSET)

        limit = d.pop("limit", UNSET)

        get_instance_logs_request = cls(
            uuid=uuid,
            name=name,
            offset=offset,
            limit=limit,
        )

        get_instance_logs_request.additional_properties = d
        return get_instance_logs_request

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
