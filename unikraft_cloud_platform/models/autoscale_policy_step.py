from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AutoscalePolicyStep")


@_attrs_define
class AutoscalePolicyStep:
    adjustment: Union[Unset, int] = UNSET
    """ The adjustment value for the step. """
    lower_bound: Union[Unset, int] = UNSET
    """ Lower bound for the step. """
    upper_bound: Union[Unset, int] = UNSET
    """ Upper bound for the step. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        adjustment = self.adjustment

        lower_bound = self.lower_bound

        upper_bound = self.upper_bound

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if adjustment is not UNSET:
            field_dict["adjustment"] = adjustment
        if lower_bound is not UNSET:
            field_dict["lower_bound"] = lower_bound
        if upper_bound is not UNSET:
            field_dict["upper_bound"] = upper_bound

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        adjustment = d.pop("adjustment", UNSET)

        lower_bound = d.pop("lower_bound", UNSET)

        upper_bound = d.pop("upper_bound", UNSET)

        autoscale_policy_step = cls(
            adjustment=adjustment,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )

        autoscale_policy_step.additional_properties = d
        return autoscale_policy_step

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
