from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="QuotasLimits")


@_attrs_define
class QuotasLimits:
    min_memory_mb: Union[Unset, int] = UNSET
    """ Minimum amount of memory assigned to live instances in megabytes """
    max_memory_mb: Union[Unset, int] = UNSET
    """ Maximum amount of memory assigned to live instances in megabytes """
    min_volume_mb: Union[Unset, int] = UNSET
    """ Minimum size of a volume in megabytes """
    max_volume_mb: Union[Unset, int] = UNSET
    """ Maximum size of a volume in megabytes """
    min_autoscale_size: Union[Unset, int] = UNSET
    """ Minimum size of an autoscale group """
    max_autoscale_size: Union[Unset, int] = UNSET
    """ Maximum size of an autoscale group """
    min_vcpus: Union[Unset, int] = UNSET
    """ Minimum number of vCPUs """
    max_vcpus: Union[Unset, int] = UNSET
    """ Maximum number of vCPUs """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        min_memory_mb = self.min_memory_mb

        max_memory_mb = self.max_memory_mb

        min_volume_mb = self.min_volume_mb

        max_volume_mb = self.max_volume_mb

        min_autoscale_size = self.min_autoscale_size

        max_autoscale_size = self.max_autoscale_size

        min_vcpus = self.min_vcpus

        max_vcpus = self.max_vcpus

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if min_memory_mb is not UNSET:
            field_dict["min_memory_mb"] = min_memory_mb
        if max_memory_mb is not UNSET:
            field_dict["max_memory_mb"] = max_memory_mb
        if min_volume_mb is not UNSET:
            field_dict["min_volume_mb"] = min_volume_mb
        if max_volume_mb is not UNSET:
            field_dict["max_volume_mb"] = max_volume_mb
        if min_autoscale_size is not UNSET:
            field_dict["min_autoscale_size"] = min_autoscale_size
        if max_autoscale_size is not UNSET:
            field_dict["max_autoscale_size"] = max_autoscale_size
        if min_vcpus is not UNSET:
            field_dict["min_vcpus"] = min_vcpus
        if max_vcpus is not UNSET:
            field_dict["max_vcpus"] = max_vcpus

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        min_memory_mb = d.pop("min_memory_mb", UNSET)

        max_memory_mb = d.pop("max_memory_mb", UNSET)

        min_volume_mb = d.pop("min_volume_mb", UNSET)

        max_volume_mb = d.pop("max_volume_mb", UNSET)

        min_autoscale_size = d.pop("min_autoscale_size", UNSET)

        max_autoscale_size = d.pop("max_autoscale_size", UNSET)

        min_vcpus = d.pop("min_vcpus", UNSET)

        max_vcpus = d.pop("max_vcpus", UNSET)

        quotas_limits = cls(
            min_memory_mb=min_memory_mb,
            max_memory_mb=max_memory_mb,
            min_volume_mb=min_volume_mb,
            max_volume_mb=max_volume_mb,
            min_autoscale_size=min_autoscale_size,
            max_autoscale_size=max_autoscale_size,
            min_vcpus=min_vcpus,
            max_vcpus=max_vcpus,
        )

        quotas_limits.additional_properties = d
        return quotas_limits

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
