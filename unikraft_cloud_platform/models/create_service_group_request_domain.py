from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.name_or_uuid import NameOrUUID


T = TypeVar("T", bound="CreateServiceGroupRequestDomain")


@_attrs_define
class CreateServiceGroupRequestDomain:
    """A domain name"""

    name: str
    """ Publicly accessible domain name.  If this name ends in a period `.` it must
    be a valid Full Qualified Domain Name (FQDN), otherwise it will become a
    subdomain of the target metro. """
    certificate: Union[Unset, "NameOrUUID"] = UNSET
    """ An identifier for a resource.  Either a name or a UUID. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        certificate: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.certificate, Unset):
            certificate = self.certificate.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if certificate is not UNSET:
            field_dict["certificate"] = certificate

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.name_or_uuid import NameOrUUID

        d = dict(src_dict)
        name = d.pop("name")

        _certificate = d.pop("certificate", UNSET)
        certificate: Union[Unset, NameOrUUID]
        if isinstance(_certificate, Unset):
            certificate = UNSET
        else:
            certificate = NameOrUUID.from_dict(_certificate)

        create_service_group_request_domain = cls(
            name=name,
            certificate=certificate,
        )

        create_service_group_request_domain.additional_properties = d
        return create_service_group_request_domain

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
