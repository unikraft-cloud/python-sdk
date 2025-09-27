from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.instance_scale_to_zero_policy import InstanceScaleToZeroPolicy, check_instance_scale_to_zero_policy
from ..types import UNSET, Unset

T = TypeVar("T", bound="InstanceScaleToZero")


@_attrs_define
class InstanceScaleToZero:
    """Scale-to-zero defines the configuration for scaling the instance to zero.
    When an instance is scaled-to-zero it can be either stopped (and fully
    shutdown) or paused wherein the state of the instance is preserved (e.g., RAM
    contents) and the instance can be resumed later without losing its state,
    i.e. "stateful".

    """

    enabled: Union[Unset, bool] = UNSET
    """ Indicates whether scale-to-zero is enabled for the instance. """
    policy: Union[Unset, InstanceScaleToZeroPolicy] = UNSET
    """ The specific policy to use for scaling the instance to zero. """
    stateful: Union[Unset, bool] = UNSET
    """ Whether the instance should be stateful when scaled to zero. If set to
    true, the instance will retain its state (e.g., RAM contents) when scaled
    to zero.  This is useful for instances that need to maintain their state
    across scale-to-zero operations.  If set to false, the instance will lose
    its state when scaled to zero, and it will be restarted from scratch when
    scaled back up. """
    cooldown_time_ms: Union[Unset, int] = UNSET
    """ The cooldown time in milliseconds before the instance can be scaled to
    zero again.  This is useful to prevent rapid scaling to zero and back up,
    which can lead to performance issues or resource exhaustion. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        enabled = self.enabled

        policy: Union[Unset, str] = UNSET
        if not isinstance(self.policy, Unset):
            policy = self.policy

        stateful = self.stateful

        cooldown_time_ms = self.cooldown_time_ms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if policy is not UNSET:
            field_dict["policy"] = policy
        if stateful is not UNSET:
            field_dict["stateful"] = stateful
        if cooldown_time_ms is not UNSET:
            field_dict["cooldown_time_ms"] = cooldown_time_ms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        enabled = d.pop("enabled", UNSET)

        _policy = d.pop("policy", UNSET)
        policy: Union[Unset, InstanceScaleToZeroPolicy]
        if isinstance(_policy, Unset):
            policy = UNSET
        else:
            policy = check_instance_scale_to_zero_policy(_policy)

        stateful = d.pop("stateful", UNSET)

        cooldown_time_ms = d.pop("cooldown_time_ms", UNSET)

        instance_scale_to_zero = cls(
            enabled=enabled,
            policy=policy,
            stateful=stateful,
            cooldown_time_ms=cooldown_time_ms,
        )

        instance_scale_to_zero.additional_properties = d
        return instance_scale_to_zero

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
