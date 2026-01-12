from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_instance_logs_response_logged_instance import GetInstanceLogsResponseLoggedInstance


T = TypeVar("T", bound="GetInstanceLogsResponseData")


@_attrs_define
class GetInstanceLogsResponseData:
    instances: Union[Unset, list["GetInstanceLogsResponseLoggedInstance"]] = UNSET
    """ The instance which this requested waited on.

    Note: only one instance can be specified in the request, so this will
    always contain a single entry. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        instances: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.instances, Unset):
            instances = []
            for instances_item_data in self.instances:
                instances_item = instances_item_data.to_dict()
                instances.append(instances_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if instances is not UNSET:
            field_dict["instances"] = instances

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_instance_logs_response_logged_instance import GetInstanceLogsResponseLoggedInstance

        d = dict(src_dict)
        instances = []
        _instances = d.pop("instances", UNSET)
        for instances_item_data in _instances or []:
            instances_item = GetInstanceLogsResponseLoggedInstance.from_dict(instances_item_data)

            instances.append(instances_item)

        get_instance_logs_response_data = cls(
            instances=instances,
        )

        get_instance_logs_response_data.additional_properties = d
        return get_instance_logs_response_data

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
