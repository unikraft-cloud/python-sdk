from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

T = TypeVar("T", bound="DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse")


@_attrs_define
class DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse:
    status: Union[Unset, ResponseStatus] = UNSET
    """ The response status of an API request. """
    name: Union[Unset, str] = UNSET
    """ The name of the service of the deleted policy. """
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

        name = self.name

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if status is not UNSET:
            field_dict["status"] = status
        if name is not UNSET:
            field_dict["name"] = name
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        name = d.pop("name", UNSET)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        delete_autoscale_configuration_policy_response_policies_response = cls(
            status=status,
            name=name,
            message=message,
            error=error,
        )

        delete_autoscale_configuration_policy_response_policies_response.additional_properties = d
        return delete_autoscale_configuration_policy_response_policies_response

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
