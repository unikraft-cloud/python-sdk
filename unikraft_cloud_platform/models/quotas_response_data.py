from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.quotas import Quotas


T = TypeVar("T", bound="QuotasResponseData")


@_attrs_define
class QuotasResponseData:
    quotas: Union[Unset, list["Quotas"]] = UNSET
    """ The quota(s) which were retrieved by the request. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        quotas: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.quotas, Unset):
            quotas = []
            for quotas_item_data in self.quotas:
                quotas_item = quotas_item_data.to_dict()
                quotas.append(quotas_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if quotas is not UNSET:
            field_dict["quotas"] = quotas

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.quotas import Quotas

        d = dict(src_dict)
        quotas = []
        _quotas = d.pop("quotas", UNSET)
        for quotas_item_data in _quotas or []:
            quotas_item = Quotas.from_dict(quotas_item_data)

            quotas.append(quotas_item)

        quotas_response_data = cls(
            quotas=quotas,
        )

        quotas_response_data.additional_properties = d
        return quotas_response_data

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
