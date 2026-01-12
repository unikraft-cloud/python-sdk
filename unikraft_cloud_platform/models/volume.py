import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.response_status import ResponseStatus, check_response_status
from ..models.volume_state import VolumeState, check_volume_state
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.volume_instance_id import VolumeInstanceID
    from ..models.volume_volume_instance_mount import VolumeVolumeInstanceMount


T = TypeVar("T", bound="Volume")


@_attrs_define
class Volume:
    """A volume represents a storage device that can be attached to an instance."""

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the volume.

    This is a unique identifier for the volume that is generated when the
    volume is created.  The UUID is used to reference the volume in
    API calls and can be used to identify the volume in all API calls that
    require an identifier. """
    name: Union[Unset, str] = UNSET
    """ The name of the volume.

    This is a human-readable name that can be used to identify the volume.
    The name must be unique within the context of your account.  The name can
    also be used to identify the volume in API calls. """
    created_at: Union[Unset, datetime.datetime] = UNSET
    """ The time the volume was created. """
    state: Union[Unset, VolumeState] = UNSET
    """ Current state of the volume. """
    size_mb: Union[Unset, int] = UNSET
    """ The size of the volume in megabytes. """
    persistent: Union[Unset, bool] = UNSET
    """ Indicates if the volume will stay alive when the last instance is deleted
    that this volume is attached to. """
    attached_to: Union[Unset, list["VolumeInstanceID"]] = UNSET
    """ List of instances that this volume is attached to. """
    mounted_by: Union[Unset, list["VolumeVolumeInstanceMount"]] = UNSET
    """ List of instances that have this volume mounted. """
    tags: Union[Unset, list[str]] = UNSET
    """ The tags associated with the volume. """
    status: Union[Unset, ResponseStatus] = UNSET
    """ The response status of an API request. """
    message: Union[Unset, str] = UNSET
    """ An optional message providing additional information about the status.
    This field is only set when this message object is used as a response
    message, and is useful when the status is not `success`. """
    error: Union[Unset, int] = UNSET
    """ An optional error code providing additional information about the status.
    This field is only set when this message object is used as a response
    message, and is useful when the status is not `success`. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        created_at: Union[Unset, str] = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        state: Union[Unset, str] = UNSET
        if not isinstance(self.state, Unset):
            state = self.state

        size_mb = self.size_mb

        persistent = self.persistent

        attached_to: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.attached_to, Unset):
            attached_to = []
            for attached_to_item_data in self.attached_to:
                attached_to_item = attached_to_item_data.to_dict()
                attached_to.append(attached_to_item)

        mounted_by: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.mounted_by, Unset):
            mounted_by = []
            for mounted_by_item_data in self.mounted_by:
                mounted_by_item = mounted_by_item_data.to_dict()
                mounted_by.append(mounted_by_item)

        tags: Union[Unset, list[str]] = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags

        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if state is not UNSET:
            field_dict["state"] = state
        if size_mb is not UNSET:
            field_dict["size_mb"] = size_mb
        if persistent is not UNSET:
            field_dict["persistent"] = persistent
        if attached_to is not UNSET:
            field_dict["attached_to"] = attached_to
        if mounted_by is not UNSET:
            field_dict["mounted_by"] = mounted_by
        if tags is not UNSET:
            field_dict["tags"] = tags
        if status is not UNSET:
            field_dict["status"] = status
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.volume_instance_id import VolumeInstanceID
        from ..models.volume_volume_instance_mount import VolumeVolumeInstanceMount

        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        _created_at = d.pop("created_at", UNSET)
        created_at: Union[Unset, datetime.datetime]
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        _state = d.pop("state", UNSET)
        state: Union[Unset, VolumeState]
        if isinstance(_state, Unset):
            state = UNSET
        else:
            state = check_volume_state(_state)

        size_mb = d.pop("size_mb", UNSET)

        persistent = d.pop("persistent", UNSET)

        attached_to = []
        _attached_to = d.pop("attached_to", UNSET)
        for attached_to_item_data in _attached_to or []:
            attached_to_item = VolumeInstanceID.from_dict(attached_to_item_data)

            attached_to.append(attached_to_item)

        mounted_by = []
        _mounted_by = d.pop("mounted_by", UNSET)
        for mounted_by_item_data in _mounted_by or []:
            mounted_by_item = VolumeVolumeInstanceMount.from_dict(mounted_by_item_data)

            mounted_by.append(mounted_by_item)

        tags = cast(list[str], d.pop("tags", UNSET))

        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        volume = cls(
            uuid=uuid,
            name=name,
            created_at=created_at,
            state=state,
            size_mb=size_mb,
            persistent=persistent,
            attached_to=attached_to,
            mounted_by=mounted_by,
            tags=tags,
            status=status,
            message=message,
            error=error,
        )

        volume.additional_properties = d
        return volume

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
