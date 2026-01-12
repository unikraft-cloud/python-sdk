from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="StopInstancesRequestID")


@_attrs_define
class StopInstancesRequestID:
    """An identifier for the instance(s) to start."""

    uuid: UUID
    """ The UUID of the instance to stop.  Mutually exclusive with name. """
    name: str
    """ The name of the instance to stop.  Mutually exclusive with UUID. """
    force: Union[Unset, bool] = UNSET
    """ Whether to immediately force stop the instance. """
    drain_timeout_ms: Union[Unset, int] = UNSET
    """ Timeout for draining connections in milliseconds.  The instance does not
    receive new connections in the draining phase.  The instance is stopped
    when the last connection has been closed or the timeout expired.  The
    maximum timeout may vary.  Use -1 for the largest possible value.

    Note: This endpoint does not block.  Use the wait endpoint for the
    instance to reach the stopped state. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid = str(self.uuid)

        name = self.name

        force = self.force

        drain_timeout_ms = self.drain_timeout_ms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "uuid": uuid,
                "name": name,
            }
        )
        if force is not UNSET:
            field_dict["force"] = force
        if drain_timeout_ms is not UNSET:
            field_dict["drain_timeout_ms"] = drain_timeout_ms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        uuid = UUID(d.pop("uuid"))

        name = d.pop("name")

        force = d.pop("force", UNSET)

        drain_timeout_ms = d.pop("drain_timeout_ms", UNSET)

        stop_instances_request_id = cls(
            uuid=uuid,
            name=name,
            force=force,
            drain_timeout_ms=drain_timeout_ms,
        )

        stop_instances_request_id.additional_properties = d
        return stop_instances_request_id

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
