from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.autoscale_policy import AutoscalePolicy
    from ..models.create_autoscale_configuration_by_service_group_uuid_request_instance_create_args import (
        CreateAutoscaleConfigurationByServiceGroupUUIDRequestInstanceCreateArgs,
    )


T = TypeVar("T", bound="CreateAutoscaleConfigurationByServiceGroupUUIDRequest")


@_attrs_define
class CreateAutoscaleConfigurationByServiceGroupUUIDRequest:
    """The request message to create an autoscale configuration for a service group
    based on its UUID.

    """

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the service to create a configuration for.
    Mutually exclusive with name. """
    min_size: Union[Unset, int] = UNSET
    """ The minimum number of instances to keep running. """
    max_size: Union[Unset, int] = UNSET
    """ The maximum number of instances to keep running. """
    warmup_time_ms: Union[Unset, int] = UNSET
    """ The warmup time in milliseconds for new instances. """
    cooldown_time_ms: Union[Unset, int] = UNSET
    """ The cooldown time in milliseconds for the autoscale configuration. """
    create_args: Union[Unset, "CreateAutoscaleConfigurationByServiceGroupUUIDRequestInstanceCreateArgs"] = UNSET
    policies: Union[Unset, list["AutoscalePolicy"]] = UNSET
    """ The policies to apply to the autoscale configuration. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        min_size = self.min_size

        max_size = self.max_size

        warmup_time_ms = self.warmup_time_ms

        cooldown_time_ms = self.cooldown_time_ms

        create_args: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.create_args, Unset):
            create_args = self.create_args.to_dict()

        policies: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.policies, Unset):
            policies = []
            for policies_item_data in self.policies:
                policies_item = policies_item_data.to_dict()
                policies.append(policies_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if min_size is not UNSET:
            field_dict["min_size"] = min_size
        if max_size is not UNSET:
            field_dict["max_size"] = max_size
        if warmup_time_ms is not UNSET:
            field_dict["warmup_time_ms"] = warmup_time_ms
        if cooldown_time_ms is not UNSET:
            field_dict["cooldown_time_ms"] = cooldown_time_ms
        if create_args is not UNSET:
            field_dict["create_args"] = create_args
        if policies is not UNSET:
            field_dict["policies"] = policies

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autoscale_policy import AutoscalePolicy
        from ..models.create_autoscale_configuration_by_service_group_uuid_request_instance_create_args import (
            CreateAutoscaleConfigurationByServiceGroupUUIDRequestInstanceCreateArgs,
        )

        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        min_size = d.pop("min_size", UNSET)

        max_size = d.pop("max_size", UNSET)

        warmup_time_ms = d.pop("warmup_time_ms", UNSET)

        cooldown_time_ms = d.pop("cooldown_time_ms", UNSET)

        _create_args = d.pop("create_args", UNSET)
        create_args: Union[Unset, CreateAutoscaleConfigurationByServiceGroupUUIDRequestInstanceCreateArgs]
        if isinstance(_create_args, Unset):
            create_args = UNSET
        else:
            create_args = CreateAutoscaleConfigurationByServiceGroupUUIDRequestInstanceCreateArgs.from_dict(
                _create_args
            )

        policies = []
        _policies = d.pop("policies", UNSET)
        for policies_item_data in _policies or []:
            policies_item = AutoscalePolicy.from_dict(policies_item_data)

            policies.append(policies_item)

        create_autoscale_configuration_by_service_group_uuid_request = cls(
            uuid=uuid,
            min_size=min_size,
            max_size=max_size,
            warmup_time_ms=warmup_time_ms,
            cooldown_time_ms=cooldown_time_ms,
            create_args=create_args,
            policies=policies,
        )

        create_autoscale_configuration_by_service_group_uuid_request.additional_properties = d
        return create_autoscale_configuration_by_service_group_uuid_request

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
