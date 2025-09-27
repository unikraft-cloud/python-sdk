from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="CreateInstanceRequestDomain")


@_attrs_define
class CreateInstanceRequestDomain:
    """The domain configuration for the service group.

    A domain defines a publicly accessible domain name for the instance.  If
    the domain name ends with a period `.`, it must be a valid Fully Qualified
    Domain Name (FQDN), otherwise it will become a subdomain of the target
    metro.  The domain can be associated with an existing certificate by
    specifying the certificate's name or UUID.  If no certificate is specified
    and a FQDN is provided, Unikraft Cloud will automatically generate a new
    certificate for the domain based on Let's Encrypt and seek to accomplish a
    DNS-01 challenge.

    """

    name: str
    """ Publicly accessible domain name.

    If this name ends in a period `.` it must be a valid Full Qualified
    Domain Name (FQDN), e.g. `example.com.`; otherwise it will become a
    subdomain of the target metro, e.g. `example` becomes
    `example.fra0.unikraft.app`. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        create_instance_request_domain = cls(
            name=name,
        )

        create_instance_request_domain.additional_properties = d
        return create_instance_request_domain

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
