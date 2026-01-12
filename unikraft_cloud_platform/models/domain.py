from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Domain")


@_attrs_define
class Domain:
    """A domain name.

    Domain names are completely specified with all labels in the hierarchy of the
    DNS, having no parts omitted.  The domain can be associated with an existing
    certificate by specifying the certificate's name or UUID.  If no certificate
    is specified and a FQDN is provided, Unikraft Cloud will automatically
    generate a new certificate for the domain based on Let's Encrypt and seek to
    accomplish a DNS-01 challenge.

    """

    fqdn: Union[Unset, str] = UNSET
    """ Publicly accessible domain name.  If this name ends in a period `.` it must
    be a valid Full Qualified Domain Name (FQDN), otherwise it will become a
    subdomain of the target metro. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        fqdn = self.fqdn

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if fqdn is not UNSET:
            field_dict["fqdn"] = fqdn

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        fqdn = d.pop("fqdn", UNSET)

        domain = cls(
            fqdn=fqdn,
        )

        domain.additional_properties = d
        return domain

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
