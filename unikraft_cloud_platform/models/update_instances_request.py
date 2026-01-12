from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.update_instances_request_op import UpdateInstancesRequestOp, check_update_instances_request_op
from ..models.update_instances_request_prop import UpdateInstancesRequestProp, check_update_instances_request_prop
from ..types import UNSET, Unset

T = TypeVar("T", bound="UpdateInstancesRequest")


@_attrs_define
class UpdateInstancesRequest:
    """The request message for updating one or more instances."""

    prop: UpdateInstancesRequestProp
    """ The property to modify. """
    op: UpdateInstancesRequestOp
    """ The operation to perform on the property. """
    id: Union[Unset, str] = UNSET
    """ (Optional).  A client-provided identifier for tracking this operation in the response. """
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the instance to update. Mutually exclusive with name. """
    name: Union[Unset, str] = UNSET
    """ The name of the instance to update. Mutually exclusive with UUID. """
    value: Union[Unset, Any] = UNSET
    """ Represents a dynamically typed value which can be either null, a number, a string, a boolean, a recursive
    struct value, or a list of values. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        prop: str = self.prop

        op: str = self.op

        id = self.id

        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

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
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        prop = check_update_instances_request_prop(d.pop("prop"))

        op = check_update_instances_request_op(d.pop("op"))

        id = d.pop("id", UNSET)

        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        value = d.pop("value", UNSET)

        update_instances_request = cls(
            prop=prop,
            op=op,
            id=id,
            uuid=uuid,
            name=name,
            value=value,
        )

        update_instances_request.additional_properties = d
        return update_instances_request

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
