import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.certificate_state import CertificateState, check_certificate_state
from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

T = TypeVar("T", bound="Certificate")


@_attrs_define
class Certificate:
    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the certificate.

    This is a unique identifier for the certificate that is generated when the
    certificate is created.  The UUID is used to reference the certificate in
    API calls and can be used to identify the certificate in all API calls that
    require an identifier. """
    name: Union[Unset, str] = UNSET
    """ The name of the certificate.

    This is a human-readable name that can be used to identify the certificate.
    The name must be unique within the context of your account.  The name can
    also be used to identify the certificate in API calls. """
    created_at: Union[Unset, datetime.datetime] = UNSET
    """ The time the certificate was created. """
    common_name: Union[Unset, str] = UNSET
    """ The common name (CN) field from the certificate's subject.

    This is typically the primary domain name that the certificate is issued
    for. It represents the main identity that the certificate validates. """
    subject: Union[Unset, str] = UNSET
    """ The complete subject distinguished name (DN) of the certificate.

    This contains the full subject information from the certificate, including
    the common name, organization, organizational unit, locality, state, and
    country. The subject identifies the entity that the certificate is issued to. """
    issuer: Union[Unset, str] = UNSET
    """ The complete issuer distinguished name (DN) of the certificate.

    This identifies the Certificate Authority (CA) that issued the certificate.
    It contains information about the CA including its common name, organization,
    and country. """
    serial_number: Union[Unset, str] = UNSET
    """ The unique serial number assigned to the certificate by the issuing CA.

    This is a unique identifier within the scope of the issuing CA that can be
    used to identify and track the certificate. Serial numbers are typically
    represented as hexadecimal strings. """
    not_before: Union[Unset, datetime.datetime] = UNSET
    """ The date and time when the certificate becomes valid.

    The certificate should not be trusted before this date. This timestamp
    marks the beginning of the certificate's validity period. """
    not_after: Union[Unset, datetime.datetime] = UNSET
    """ The date and time when the certificate expires.

    The certificate should not be trusted after this date. This timestamp
    marks the end of the certificate's validity period. Certificates should
    be renewed before this date to maintain service availability. """
    state: Union[Unset, CertificateState] = UNSET
    """ The current state of the certificate.

    This indicates whether the certificate is pending issuance, valid and
    ready for use, or in an error state. See CertificateState enum for
    detailed state descriptions. """
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

        common_name = self.common_name

        subject = self.subject

        issuer = self.issuer

        serial_number = self.serial_number

        not_before: Union[Unset, str] = UNSET
        if not isinstance(self.not_before, Unset):
            not_before = self.not_before.isoformat()

        not_after: Union[Unset, str] = UNSET
        if not isinstance(self.not_after, Unset):
            not_after = self.not_after.isoformat()

        state: Union[Unset, str] = UNSET
        if not isinstance(self.state, Unset):
            state = self.state

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
        if common_name is not UNSET:
            field_dict["common_name"] = common_name
        if subject is not UNSET:
            field_dict["subject"] = subject
        if issuer is not UNSET:
            field_dict["issuer"] = issuer
        if serial_number is not UNSET:
            field_dict["serial_number"] = serial_number
        if not_before is not UNSET:
            field_dict["not_before"] = not_before
        if not_after is not UNSET:
            field_dict["not_after"] = not_after
        if state is not UNSET:
            field_dict["state"] = state
        if status is not UNSET:
            field_dict["status"] = status
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
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

        common_name = d.pop("common_name", UNSET)

        subject = d.pop("subject", UNSET)

        issuer = d.pop("issuer", UNSET)

        serial_number = d.pop("serial_number", UNSET)

        _not_before = d.pop("not_before", UNSET)
        not_before: Union[Unset, datetime.datetime]
        if isinstance(_not_before, Unset):
            not_before = UNSET
        else:
            not_before = isoparse(_not_before)

        _not_after = d.pop("not_after", UNSET)
        not_after: Union[Unset, datetime.datetime]
        if isinstance(_not_after, Unset):
            not_after = UNSET
        else:
            not_after = isoparse(_not_after)

        _state = d.pop("state", UNSET)
        state: Union[Unset, CertificateState]
        if isinstance(_state, Unset):
            state = UNSET
        else:
            state = check_certificate_state(_state)

        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        certificate = cls(
            uuid=uuid,
            name=name,
            created_at=created_at,
            common_name=common_name,
            subject=subject,
            issuer=issuer,
            serial_number=serial_number,
            not_before=not_before,
            not_after=not_after,
            state=state,
            status=status,
            message=message,
            error=error,
        )

        certificate.additional_properties = d
        return certificate

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
