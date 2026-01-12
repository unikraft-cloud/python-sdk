from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.quotas_limits import QuotasLimits
    from ..models.quotas_stats import QuotasStats


T = TypeVar("T", bound="Quotas")


@_attrs_define
class Quotas:
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the quota. """
    used: Union[Unset, "QuotasStats"] = UNSET
    hard: Union[Unset, "QuotasStats"] = UNSET
    limits: Union[Unset, "QuotasLimits"] = UNSET
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

        used: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.used, Unset):
            used = self.used.to_dict()

        hard: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.hard, Unset):
            hard = self.hard.to_dict()

        limits: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.limits, Unset):
            limits = self.limits.to_dict()

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
        if used is not UNSET:
            field_dict["used"] = used
        if hard is not UNSET:
            field_dict["hard"] = hard
        if limits is not UNSET:
            field_dict["limits"] = limits
        if status is not UNSET:
            field_dict["status"] = status
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.quotas_limits import QuotasLimits
        from ..models.quotas_stats import QuotasStats

        d = dict(src_dict)
        _uuid = d.pop("uuid", UNSET)
        uuid: Union[Unset, UUID]
        if isinstance(_uuid, Unset):
            uuid = UNSET
        else:
            uuid = UUID(_uuid)

        _used = d.pop("used", UNSET)
        used: Union[Unset, QuotasStats]
        if isinstance(_used, Unset):
            used = UNSET
        else:
            used = QuotasStats.from_dict(_used)

        _hard = d.pop("hard", UNSET)
        hard: Union[Unset, QuotasStats]
        if isinstance(_hard, Unset):
            hard = UNSET
        else:
            hard = QuotasStats.from_dict(_hard)

        _limits = d.pop("limits", UNSET)
        limits: Union[Unset, QuotasLimits]
        if isinstance(_limits, Unset):
            limits = UNSET
        else:
            limits = QuotasLimits.from_dict(_limits)

        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        quotas = cls(
            uuid=uuid,
            used=used,
            hard=hard,
            limits=limits,
            status=status,
            message=message,
            error=error,
        )

        quotas.additional_properties = d
        return quotas

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
