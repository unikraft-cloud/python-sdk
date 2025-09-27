from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.autoscale_policy import AutoscalePolicy


T = TypeVar("T", bound="GetAutoscaleConfigurationPolicyResponsePolicyResponse")


@_attrs_define
class GetAutoscaleConfigurationPolicyResponsePolicyResponse:
    status: Union[Unset, ResponseStatus] = UNSET
    """ The response status of an API request. """
    policy: Union[Unset, "AutoscalePolicy"] = UNSET
    """ AutoscalePolicy defines the autoscale policy for a service.
    Right now it contains fields from both the `ondemand` and `step` policies.
    They are marked both as optional, so only one of them should be set at a
    time. This is a current limitation of the API design. """
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

        policy: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.policy, Unset):
            policy = self.policy.to_dict()

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if status is not UNSET:
            field_dict["status"] = status
        if policy is not UNSET:
            field_dict["policy"] = policy
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autoscale_policy import AutoscalePolicy

        d = dict(src_dict)
        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        _policy = d.pop("policy", UNSET)
        policy: Union[Unset, AutoscalePolicy]
        if isinstance(_policy, Unset):
            policy = UNSET
        else:
            policy = AutoscalePolicy.from_dict(_policy)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        get_autoscale_configuration_policy_response_policy_response = cls(
            status=status,
            policy=policy,
            message=message,
            error=error,
        )

        get_autoscale_configuration_policy_response_policy_response.additional_properties = d
        return get_autoscale_configuration_policy_response_policy_response

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
