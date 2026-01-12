from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.autoscale_policy_adjustment_type import (
    AutoscalePolicyAdjustmentType,
    check_autoscale_policy_adjustment_type,
)
from ..models.autoscale_policy_metric import AutoscalePolicyMetric, check_autoscale_policy_metric
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.autoscale_policy_step import AutoscalePolicyStep


T = TypeVar("T", bound="AutoscalePolicy")


@_attrs_define
class AutoscalePolicy:
    """AutoscalePolicy defines the autoscale policy for a service.
    Right now it contains fields from both the `ondemand` and `step` policies.
    They are marked both as optional, so only one of them should be set at a
    time. This is a current limitation of the API design.

    """

    name: Union[Unset, str] = UNSET
    """ The name of the policy. """
    enabled: Union[Unset, bool] = UNSET
    """ If the policy is enabled. """
    metric: Union[Unset, AutoscalePolicyMetric] = UNSET
    """ Metric to use for the step policy. """
    adjustment_type: Union[Unset, AutoscalePolicyAdjustmentType] = UNSET
    """ The type of adjustment to be made in the step policy. """
    steps: Union[Unset, list["AutoscalePolicyStep"]] = UNSET
    """ The steps for the step policy.
    Each step defines an adjustment value and optional bounds. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        enabled = self.enabled

        metric: Union[Unset, str] = UNSET
        if not isinstance(self.metric, Unset):
            metric = self.metric

        adjustment_type: Union[Unset, str] = UNSET
        if not isinstance(self.adjustment_type, Unset):
            adjustment_type = self.adjustment_type

        steps: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.steps, Unset):
            steps = []
            for steps_item_data in self.steps:
                steps_item = steps_item_data.to_dict()
                steps.append(steps_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if metric is not UNSET:
            field_dict["metric"] = metric
        if adjustment_type is not UNSET:
            field_dict["adjustment_type"] = adjustment_type
        if steps is not UNSET:
            field_dict["steps"] = steps

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autoscale_policy_step import AutoscalePolicyStep

        d = dict(src_dict)
        name = d.pop("name", UNSET)

        enabled = d.pop("enabled", UNSET)

        _metric = d.pop("metric", UNSET)
        metric: Union[Unset, AutoscalePolicyMetric]
        if isinstance(_metric, Unset):
            metric = UNSET
        else:
            metric = check_autoscale_policy_metric(_metric)

        _adjustment_type = d.pop("adjustment_type", UNSET)
        adjustment_type: Union[Unset, AutoscalePolicyAdjustmentType]
        if isinstance(_adjustment_type, Unset):
            adjustment_type = UNSET
        else:
            adjustment_type = check_autoscale_policy_adjustment_type(_adjustment_type)

        steps = []
        _steps = d.pop("steps", UNSET)
        for steps_item_data in _steps or []:
            steps_item = AutoscalePolicyStep.from_dict(steps_item_data)

            steps.append(steps_item)

        autoscale_policy = cls(
            name=name,
            enabled=enabled,
            metric=metric,
            adjustment_type=adjustment_type,
            steps=steps,
        )

        autoscale_policy.additional_properties = d
        return autoscale_policy

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
