from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.update_service_group_by_uuid_request_body_op import (
    UpdateServiceGroupByUUIDRequestBodyOp,
    check_update_service_group_by_uuid_request_body_op,
)
from ..models.update_service_group_by_uuid_request_body_prop import (
    UpdateServiceGroupByUUIDRequestBodyProp,
    check_update_service_group_by_uuid_request_body_prop,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="UpdateServiceGroupByUUIDRequestBody")


@_attrs_define
class UpdateServiceGroupByUUIDRequestBody:
    prop: UpdateServiceGroupByUUIDRequestBodyProp
    """ The property to modify. """
    op: UpdateServiceGroupByUUIDRequestBodyOp
    """ The operation to perform. """
    id: Union[Unset, str] = UNSET
    """ (Optional).  A client-provided identifier for tracking this operation in the response. """
    value: Union[Unset, Any] = UNSET
    """ Represents a dynamically typed value which can be either null, a number, a string, a boolean, a recursive
    struct value, or a list of values. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        prop: str = self.prop

        op: str = self.op

        id = self.id

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "prop": prop,
                "op": op,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        prop = check_update_service_group_by_uuid_request_body_prop(d.pop("prop"))

        op = check_update_service_group_by_uuid_request_body_op(d.pop("op"))

        id = d.pop("id", UNSET)

        value = d.pop("value", UNSET)

        update_service_group_by_uuid_request_body = cls(
            prop=prop,
            op=op,
            id=id,
            value=value,
        )

        update_service_group_by_uuid_request_body.additional_properties = d
        return update_service_group_by_uuid_request_body

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
