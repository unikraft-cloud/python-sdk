from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_autoscale_configurations_response_configurations_response import (
        CreateAutoscaleConfigurationsResponseConfigurationsResponse,
    )


T = TypeVar("T", bound="CreateAutoscaleConfigurationsResponseData")


@_attrs_define
class CreateAutoscaleConfigurationsResponseData:
    service_groups: Union[Unset, list["CreateAutoscaleConfigurationsResponseConfigurationsResponse"]] = UNSET
    """ The configuration(s) which were created by the request. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        service_groups: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.service_groups, Unset):
            service_groups = []
            for service_groups_item_data in self.service_groups:
                service_groups_item = service_groups_item_data.to_dict()
                service_groups.append(service_groups_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if service_groups is not UNSET:
            field_dict["service_groups"] = service_groups

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_autoscale_configurations_response_configurations_response import (
            CreateAutoscaleConfigurationsResponseConfigurationsResponse,
        )

        d = dict(src_dict)
        service_groups = []
        _service_groups = d.pop("service_groups", UNSET)
        for service_groups_item_data in _service_groups or []:
            service_groups_item = CreateAutoscaleConfigurationsResponseConfigurationsResponse.from_dict(
                service_groups_item_data
            )

            service_groups.append(service_groups_item)

        create_autoscale_configurations_response_data = cls(
            service_groups=service_groups,
        )

        create_autoscale_configurations_response_data.additional_properties = d
        return create_autoscale_configurations_response_data

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
