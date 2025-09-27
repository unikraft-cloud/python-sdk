from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_instance_logs_response_logged_instance_state import (
    GetInstanceLogsResponseLoggedInstanceState,
    check_get_instance_logs_response_logged_instance_state,
)
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_instance_logs_response_available import GetInstanceLogsResponseAvailable
    from ..models.get_instance_logs_response_range import GetInstanceLogsResponseRange


T = TypeVar("T", bound="GetInstanceLogsResponseLoggedInstance")


@_attrs_define
class GetInstanceLogsResponseLoggedInstance:
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the instance. """
    name: Union[Unset, str] = UNSET
    """ The name of the instance. """
    output: Union[Unset, str] = UNSET
    """ Base64 encoded log output of the instance. """
    available: Union[Unset, "GetInstanceLogsResponseAvailable"] = UNSET
    range_: Union[Unset, "GetInstanceLogsResponseRange"] = UNSET
    state: Union[Unset, GetInstanceLogsResponseLoggedInstanceState] = UNSET
    """ State of the instance when the logs were retrieved. """
    message: Union[Unset, str] = UNSET
    """ An optional message providing additional information about the status.
    This field is useful when the status is not `success`. """
    error: Union[Unset, int] = UNSET
    """ An optional error code providing additional information about the status.
    This field is useful when the status is not `success`. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        output = self.output

        available: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.available, Unset):
            available = self.available.to_dict()

        range_: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.range_, Unset):
            range_ = self.range_.to_dict()

        state: Union[Unset, str] = UNSET
        if not isinstance(self.state, Unset):
            state = self.state

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if output is not UNSET:
            field_dict["output"] = output
        if available is not UNSET:
            field_dict["available"] = available
        if range_ is not UNSET:
            field_dict["range"] = range_
        if state is not UNSET:
            field_dict["state"] = state
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_instance_logs_response_available import GetInstanceLogsResponseAvailable
        from ..models.get_instance_logs_response_range import GetInstanceLogsResponseRange

        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        output = d.pop("output", UNSET)

        _available = d.pop("available", UNSET)
        available: Union[Unset, GetInstanceLogsResponseAvailable]
        if isinstance(_available, Unset):
            available = UNSET
        else:
            available = GetInstanceLogsResponseAvailable.from_dict(_available)

        _range_ = d.pop("range", UNSET)
        range_: Union[Unset, GetInstanceLogsResponseRange]
        if isinstance(_range_, Unset):
            range_ = UNSET
        else:
            range_ = GetInstanceLogsResponseRange.from_dict(_range_)

        _state = d.pop("state", UNSET)
        state: Union[Unset, GetInstanceLogsResponseLoggedInstanceState]
        if isinstance(_state, Unset):
            state = UNSET
        else:
            state = check_get_instance_logs_response_logged_instance_state(_state)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        get_instance_logs_response_logged_instance = cls(
            uuid=uuid,
            name=name,
            output=output,
            available=available,
            range_=range_,
            state=state,
            message=message,
            error=error,
        )

        get_instance_logs_response_logged_instance.additional_properties = d
        return get_instance_logs_response_logged_instance

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
