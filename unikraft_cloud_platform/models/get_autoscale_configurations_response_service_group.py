from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.autoscale_policy import AutoscalePolicy
    from ..models.service_group_template import ServiceGroupTemplate


T = TypeVar("T", bound="GetAutoscaleConfigurationsResponseServiceGroup")


@_attrs_define
class GetAutoscaleConfigurationsResponseServiceGroup:
    status: Union[Unset, ResponseStatus] = UNSET
    """ The response status of an API request. """
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the service where the configuration was created. """
    name: Union[Unset, str] = UNSET
    """ The name of the service where the configuration was created. """
    enabled: Union[Unset, bool] = UNSET
    """ If the autoscale configuration is enabled. """
    min_size: Union[Unset, int] = UNSET
    """ The minimum number of instances to keep running.
    Only if enabled is true. """
    max_size: Union[Unset, int] = UNSET
    """ The maximum number of instances to keep running.
    Only if enabled is true. """
    warmup_time_ms: Union[Unset, int] = UNSET
    """ The warmup time in seconds for new instances.
    Only if enabled is true. """
    cooldown_time_ms: Union[Unset, int] = UNSET
    """ The cooldown time in seconds for the autoscale configuration.
    Only if enabled is true. """
    template: Union[Unset, "ServiceGroupTemplate"] = UNSET
    policies: Union[Unset, list["AutoscalePolicy"]] = UNSET
    """ The policies applied to the autoscale configuration. """
    message: Union[Unset, str] = UNSET
    """ An optional message providing additional information about the status.
    This field is useful when the status is not `success`. """
    error: Union[Unset, int] = UNSET
    """ An optional error code providing additional information about the status.
    This field is useful when the status is not `success`. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status

        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        enabled = self.enabled

        min_size = self.min_size

        max_size = self.max_size

        warmup_time_ms = self.warmup_time_ms

        cooldown_time_ms = self.cooldown_time_ms

        template: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.template, Unset):
            template = self.template.to_dict()

        policies: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.policies, Unset):
            policies = []
            for policies_item_data in self.policies:
                policies_item = policies_item_data.to_dict()
                policies.append(policies_item)

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if status is not UNSET:
            field_dict["status"] = status
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if min_size is not UNSET:
            field_dict["min_size"] = min_size
        if max_size is not UNSET:
            field_dict["max_size"] = max_size
        if warmup_time_ms is not UNSET:
            field_dict["warmup_time_ms"] = warmup_time_ms
        if cooldown_time_ms is not UNSET:
            field_dict["cooldown_time_ms"] = cooldown_time_ms
        if template is not UNSET:
            field_dict["template"] = template
        if policies is not UNSET:
            field_dict["policies"] = policies
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autoscale_policy import AutoscalePolicy
        from ..models.service_group_template import ServiceGroupTemplate

        d = dict(src_dict)
        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        enabled = d.pop("enabled", UNSET)

        min_size = d.pop("min_size", UNSET)

        max_size = d.pop("max_size", UNSET)

        warmup_time_ms = d.pop("warmup_time_ms", UNSET)

        cooldown_time_ms = d.pop("cooldown_time_ms", UNSET)

        _template = d.pop("template", UNSET)
        template: Union[Unset, ServiceGroupTemplate]
        if isinstance(_template, Unset):
            template = UNSET
        else:
            template = ServiceGroupTemplate.from_dict(_template)

        policies = []
        _policies = d.pop("policies", UNSET)
        for policies_item_data in _policies or []:
            policies_item = AutoscalePolicy.from_dict(policies_item_data)

            policies.append(policies_item)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        get_autoscale_configurations_response_service_group = cls(
            status=status,
            uuid=uuid,
            name=name,
            enabled=enabled,
            min_size=min_size,
            max_size=max_size,
            warmup_time_ms=warmup_time_ms,
            cooldown_time_ms=cooldown_time_ms,
            template=template,
            policies=policies,
            message=message,
            error=error,
        )

        get_autoscale_configurations_response_service_group.additional_properties = d
        return get_autoscale_configurations_response_service_group

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
