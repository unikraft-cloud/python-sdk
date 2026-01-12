from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.autoscale_policy import AutoscalePolicy


T = TypeVar("T", bound="CreateAutoscaleConfigurationPolicyRequest")


@_attrs_define
class CreateAutoscaleConfigurationPolicyRequest:
    """The request message to create an autoscale configuration policy for a
    service.

    """

    name: str
    """ The Name of the service to add a policy to. """
    type_: "AutoscalePolicy"
    """ AutoscalePolicy defines the autoscale policy for a service.
    Right now it contains fields from both the `ondemand` and `step` policies.
    They are marked both as optional, so only one of them should be set at a
    time. This is a current limitation of the API design. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        type_ = self.type_.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "type": type_,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autoscale_policy import AutoscalePolicy

        d = dict(src_dict)
        name = d.pop("name")

        type_ = AutoscalePolicy.from_dict(d.pop("type"))

        create_autoscale_configuration_policy_request = cls(
            name=name,
            type_=type_,
        )

        create_autoscale_configuration_policy_request.additional_properties = d
        return create_autoscale_configuration_policy_request

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
