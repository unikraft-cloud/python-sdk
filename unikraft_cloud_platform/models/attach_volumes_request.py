from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.attach_volumes_request_instance_id import AttachVolumesRequestInstanceID


T = TypeVar("T", bound="AttachVolumesRequest")


@_attrs_define
class AttachVolumesRequest:
    """The request message for attaching one or more volume(s) to instances by
    their UUID(s) or name(s).

    """

    attach_to: "AttachVolumesRequestInstanceID"
    """ Reference to the instance to attach the volume to. """
    at: str
    """ Path of the mountpoint.

    The path must be absolute, not contain `.` and `..` components, and not
    contain colons (`:`). The path must point to an empty directory. If the
    directory does not exist, it is created. """
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the volume to attach. Mutually exclusive with name.
    Exactly one of uuid or name must be provided. """
    name: Union[Unset, str] = UNSET
    """ The name of the volume to attach. Mutually exclusive with UUID.
    Exactly one of uuid or name must be provided. """
    readonly: Union[Unset, bool] = UNSET
    """ Whether the volume should be mounted read-only. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        attach_to = self.attach_to.to_dict()

        at = self.at

        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        readonly = self.readonly

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "attach_to": attach_to,
                "at": at,
            }
        )
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if readonly is not UNSET:
            field_dict["readonly"] = readonly

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.attach_volumes_request_instance_id import AttachVolumesRequestInstanceID

        d = dict(src_dict)
        attach_to = AttachVolumesRequestInstanceID.from_dict(d.pop("attach_to"))

        at = d.pop("at")

        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        readonly = d.pop("readonly", UNSET)

        attach_volumes_request = cls(
            attach_to=attach_to,
            at=at,
            uuid=uuid,
            name=name,
            readonly=readonly,
        )

        attach_volumes_request.additional_properties = d
        return attach_volumes_request

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
