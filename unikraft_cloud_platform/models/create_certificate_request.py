from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="CreateCertificateRequest")


@_attrs_define
class CreateCertificateRequest:
    """The request message for creating/uploading a new certificate."""

    cn: str
    """ The common name (CN) of the certificate. """
    chain: str
    """ The chain of the certificate. """
    pkey: str
    """ The private key of the certificate. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cn = self.cn

        chain = self.chain

        pkey = self.pkey

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "cn": cn,
                "chain": chain,
                "pkey": pkey,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        cn = d.pop("cn")

        chain = d.pop("chain")

        pkey = d.pop("pkey")

        create_certificate_request = cls(
            cn=cn,
            chain=chain,
            pkey=pkey,
        )

        create_certificate_request.additional_properties = d
        return create_certificate_request

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
