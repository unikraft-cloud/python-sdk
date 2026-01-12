from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.stop_instance_response_stopped_instance_previous_state import (
    StopInstanceResponseStoppedInstancePreviousState,
    check_stop_instance_response_stopped_instance_previous_state,
)
from ..models.stop_instance_response_stopped_instance_state import (
    StopInstanceResponseStoppedInstanceState,
    check_stop_instance_response_stopped_instance_state,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="StopInstanceResponseStoppedInstance")


@_attrs_define
class StopInstanceResponseStoppedInstance:
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the instance. """
    name: Union[Unset, str] = UNSET
    """ The name of the instance. """
    state: Union[Unset, StopInstanceResponseStoppedInstanceState] = UNSET
    """ The current state of the instance. """
    previous_state: Union[Unset, StopInstanceResponseStoppedInstancePreviousState] = UNSET
    """ The previous state of the instance before the stop operation was invoked. """
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

        state: Union[Unset, str] = UNSET
        if not isinstance(self.state, Unset):
            state = self.state

        previous_state: Union[Unset, str] = UNSET
        if not isinstance(self.previous_state, Unset):
            previous_state = self.previous_state

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if state is not UNSET:
            field_dict["state"] = state
        if previous_state is not UNSET:
            field_dict["previous_state"] = previous_state
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        _state = d.pop("state", UNSET)
        state: Union[Unset, StopInstanceResponseStoppedInstanceState]
        if isinstance(_state, Unset):
            state = UNSET
        else:
            state = check_stop_instance_response_stopped_instance_state(_state)

        _previous_state = d.pop("previous_state", UNSET)
        previous_state: Union[Unset, StopInstanceResponseStoppedInstancePreviousState]
        if isinstance(_previous_state, Unset):
            previous_state = UNSET
        else:
            previous_state = check_stop_instance_response_stopped_instance_previous_state(_previous_state)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        stop_instance_response_stopped_instance = cls(
            uuid=uuid,
            name=name,
            state=state,
            previous_state=previous_state,
            message=message,
            error=error,
        )

        stop_instance_response_stopped_instance.additional_properties = d
        return stop_instance_response_stopped_instance

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
