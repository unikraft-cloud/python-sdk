from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.certificate import Certificate


T = TypeVar("T", bound="CreateCertificateResponseData")


@_attrs_define
class CreateCertificateResponseData:
    certificates: Union[Unset, list["Certificate"]] = UNSET
    """ The certificate which was created by this request.

    Note: only one certificate can be specified in the request, so this
    will always contain a single entry. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        certificates: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.certificates, Unset):
            certificates = []
            for certificates_item_data in self.certificates:
                certificates_item = certificates_item_data.to_dict()
                certificates.append(certificates_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if certificates is not UNSET:
            field_dict["certificates"] = certificates

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.certificate import Certificate

        d = dict(src_dict)
        certificates = []
        _certificates = d.pop("certificates", UNSET)
        for certificates_item_data in _certificates or []:
            certificates_item = Certificate.from_dict(certificates_item_data)

            certificates.append(certificates_item)

        create_certificate_response_data = cls(
            certificates=certificates,
        )

        create_certificate_response_data.additional_properties = d
        return create_certificate_response_data

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
