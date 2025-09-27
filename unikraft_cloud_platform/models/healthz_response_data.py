from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.healthz_response_data_services import HealthzResponseDataServices


T = TypeVar("T", bound="HealthzResponseData")


@_attrs_define
class HealthzResponseData:
    """For now, no additional data is returned by the health check."""

    services: Union[Unset, "HealthzResponseDataServices"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        services: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.services, Unset):
            services = self.services.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if services is not UNSET:
            field_dict["services"] = services

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.healthz_response_data_services import HealthzResponseDataServices

        d = dict(src_dict)
        _services = d.pop("services", UNSET)
        services: Union[Unset, HealthzResponseDataServices]
        if isinstance(_services, Unset):
            services = UNSET
        else:
            services = HealthzResponseDataServices.from_dict(_services)

        healthz_response_data = cls(
            services=services,
        )

        healthz_response_data.additional_properties = d
        return healthz_response_data

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
