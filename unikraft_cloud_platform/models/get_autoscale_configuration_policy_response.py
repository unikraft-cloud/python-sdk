from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_autoscale_configuration_policy_response_data import GetAutoscaleConfigurationPolicyResponseData
    from ..models.response_error import ResponseError


T = TypeVar("T", bound="GetAutoscaleConfigurationPolicyResponse")


@_attrs_define
class GetAutoscaleConfigurationPolicyResponse:
    status: Union[Unset, ResponseStatus] = UNSET
    """ The response status of an API request. """
    data: Union[Unset, "GetAutoscaleConfigurationPolicyResponseData"] = UNSET
    errors: Union[Unset, list["ResponseError"]] = UNSET
    """ A list of errors which may have occurred during the request. """
    op_time_us: Union[Unset, int] = UNSET
    """ The operation time in microseconds.  This is the time it took to process
    the request and generate the response. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status

        data: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        errors: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.errors, Unset):
            errors = []
            for errors_item_data in self.errors:
                errors_item = errors_item_data.to_dict()
                errors.append(errors_item)

        op_time_us = self.op_time_us

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if status is not UNSET:
            field_dict["status"] = status
        if data is not UNSET:
            field_dict["data"] = data
        if errors is not UNSET:
            field_dict["errors"] = errors
        if op_time_us is not UNSET:
            field_dict["op_time_us"] = op_time_us

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_autoscale_configuration_policy_response_data import (
            GetAutoscaleConfigurationPolicyResponseData,
        )
        from ..models.response_error import ResponseError

        d = dict(src_dict)
        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        _data = d.pop("data", UNSET)
        data: Union[Unset, GetAutoscaleConfigurationPolicyResponseData]
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = GetAutoscaleConfigurationPolicyResponseData.from_dict(_data)

        errors = []
        _errors = d.pop("errors", UNSET)
        for errors_item_data in _errors or []:
            errors_item = ResponseError.from_dict(errors_item_data)

            errors.append(errors_item)

        op_time_us = d.pop("op_time_us", UNSET)

        get_autoscale_configuration_policy_response = cls(
            status=status,
            data=data,
            errors=errors,
            op_time_us=op_time_us,
        )

        get_autoscale_configuration_policy_response.additional_properties = d
        return get_autoscale_configuration_policy_response

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
