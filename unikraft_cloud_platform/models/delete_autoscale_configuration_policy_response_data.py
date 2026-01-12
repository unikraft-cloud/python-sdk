from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.delete_autoscale_configuration_policy_response_policies_response import (
        DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse,
    )


T = TypeVar("T", bound="DeleteAutoscaleConfigurationPolicyResponseData")


@_attrs_define
class DeleteAutoscaleConfigurationPolicyResponseData:
    policies: Union[Unset, list["DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse"]] = UNSET
    """ The policies which were deleted by the request. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        policies: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.policies, Unset):
            policies = []
            for policies_item_data in self.policies:
                policies_item = policies_item_data.to_dict()
                policies.append(policies_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if policies is not UNSET:
            field_dict["policies"] = policies

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.delete_autoscale_configuration_policy_response_policies_response import (
            DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse,
        )

        d = dict(src_dict)
        policies = []
        _policies = d.pop("policies", UNSET)
        for policies_item_data in _policies or []:
            policies_item = DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse.from_dict(policies_item_data)

            policies.append(policies_item)

        delete_autoscale_configuration_policy_response_data = cls(
            policies=policies,
        )

        delete_autoscale_configuration_policy_response_data.additional_properties = d
        return delete_autoscale_configuration_policy_response_data

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
