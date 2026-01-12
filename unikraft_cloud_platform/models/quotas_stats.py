from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="QuotasStats")


@_attrs_define
class QuotasStats:
    instances: Union[Unset, int] = UNSET
    """ Number of instances """
    live_instances: Union[Unset, int] = UNSET
    """ Number of instances that are not in the `stopped` state """
    live_vcpus: Union[Unset, int] = UNSET
    """ Number of vCPUs """
    live_memory_mb: Union[Unset, int] = UNSET
    """ Amount of memory assigned to instances that are not in the `stopped`
    state in megabytes """
    service_groups: Union[Unset, int] = UNSET
    """ Number of services """
    services: Union[Unset, int] = UNSET
    """ Number of published network ports over all existing services """
    volumes: Union[Unset, int] = UNSET
    """ Number of volumes """
    total_volume_mb: Union[Unset, int] = UNSET
    """ Total size of all volumes in megabytes """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        instances = self.instances

        live_instances = self.live_instances

        live_vcpus = self.live_vcpus

        live_memory_mb = self.live_memory_mb

        service_groups = self.service_groups

        services = self.services

        volumes = self.volumes

        total_volume_mb = self.total_volume_mb

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if instances is not UNSET:
            field_dict["instances"] = instances
        if live_instances is not UNSET:
            field_dict["live_instances"] = live_instances
        if live_vcpus is not UNSET:
            field_dict["live_vcpus"] = live_vcpus
        if live_memory_mb is not UNSET:
            field_dict["live_memory_mb"] = live_memory_mb
        if service_groups is not UNSET:
            field_dict["service_groups"] = service_groups
        if services is not UNSET:
            field_dict["services"] = services
        if volumes is not UNSET:
            field_dict["volumes"] = volumes
        if total_volume_mb is not UNSET:
            field_dict["total_volume_mb"] = total_volume_mb

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        instances = d.pop("instances", UNSET)

        live_instances = d.pop("live_instances", UNSET)

        live_vcpus = d.pop("live_vcpus", UNSET)

        live_memory_mb = d.pop("live_memory_mb", UNSET)

        service_groups = d.pop("service_groups", UNSET)

        services = d.pop("services", UNSET)

        volumes = d.pop("volumes", UNSET)

        total_volume_mb = d.pop("total_volume_mb", UNSET)

        quotas_stats = cls(
            instances=instances,
            live_instances=live_instances,
            live_vcpus=live_vcpus,
            live_memory_mb=live_memory_mb,
            service_groups=service_groups,
            services=services,
            volumes=volumes,
            total_volume_mb=total_volume_mb,
        )

        quotas_stats.additional_properties = d
        return quotas_stats

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
