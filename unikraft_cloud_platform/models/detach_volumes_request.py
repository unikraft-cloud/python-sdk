from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.detach_volumes_request_instance_id import DetachVolumesRequestInstanceID


T = TypeVar("T", bound="DetachVolumesRequest")


@_attrs_define
class DetachVolumesRequest:
    """The request message for detaching one or more volume(s) from instances by
    their UUID(s) or name(s).

    """

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the volume to detach. Mutually exclusive with name.
    Exactly one of uuid or name must be provided. """
    name: Union[Unset, str] = UNSET
    """ The name of the volume to detach. Mutually exclusive with UUID.
    Exactly one of uuid or name must be provided. """
    from_: Union[Unset, "DetachVolumesRequestInstanceID"] = UNSET
    """ Reference to the instance to detach the volume from. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        name = self.name

        from_: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.from_, Unset):
            from_ = self.from_.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if name is not UNSET:
            field_dict["name"] = name
        if from_ is not UNSET:
            field_dict["from"] = from_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.detach_volumes_request_instance_id import DetachVolumesRequestInstanceID

        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        name = d.pop("name", UNSET)

        _from_ = d.pop("from", UNSET)
        from_: Union[Unset, DetachVolumesRequestInstanceID]
        if isinstance(_from_, Unset):
            from_ = UNSET
        else:
            from_ = DetachVolumesRequestInstanceID.from_dict(_from_)

        detach_volumes_request = cls(
            uuid=uuid,
            name=name,
            from_=from_,
        )

        detach_volumes_request.additional_properties = d
        return detach_volumes_request

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
