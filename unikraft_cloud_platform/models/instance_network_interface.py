from collections.abc import Mapping
from typing import Any, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="InstanceNetworkInterface")


@_attrs_define
class InstanceNetworkInterface:
    """An instance network interface."""

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the network interface. This is a unique identifier for the
    network interface that is generated when the instance is created. """
    private_ip: Union[Unset, str] = UNSET
    """ The private IP address of the network interface. This is the internal IP
    address that is used for communication between instances within the same
    network. """
    mac: Union[Unset, str] = UNSET
    """ The MAC address of the network interface. """
    rx_bytes: Union[Unset, int] = UNSET
    """ Amount of bytes received from interface. """
    rx_packets: Union[Unset, int] = UNSET
    """ Count of packets received from interface """
    tx_bytes: Union[Unset, int] = UNSET
    """ Amount of bytes sent to interface. """
    tx_packets: Union[Unset, int] = UNSET
    """ Count of packets sent to interface """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uuid: Union[Unset, str] = UNSET
        if not isinstance(self.uuid, Unset):
            uuid = str(self.uuid)

        private_ip = self.private_ip

        mac = self.mac

        rx_bytes = self.rx_bytes

        rx_packets = self.rx_packets

        tx_bytes = self.tx_bytes

        tx_packets = self.tx_packets

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if uuid is not UNSET:
            field_dict["uuid"] = uuid
        if private_ip is not UNSET:
            field_dict["private_ip"] = private_ip
        if mac is not UNSET:
            field_dict["mac"] = mac
        if rx_bytes is not UNSET:
            field_dict["rx_bytes"] = rx_bytes
        if rx_packets is not UNSET:
            field_dict["rx_packets"] = rx_packets
        if tx_bytes is not UNSET:
            field_dict["tx_bytes"] = tx_bytes
        if tx_packets is not UNSET:
            field_dict["tx_packets"] = tx_packets

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

        private_ip = d.pop("private_ip", UNSET)

        mac = d.pop("mac", UNSET)

        rx_bytes = d.pop("rx_bytes", UNSET)

        rx_packets = d.pop("rx_packets", UNSET)

        tx_bytes = d.pop("tx_bytes", UNSET)

        tx_packets = d.pop("tx_packets", UNSET)

        instance_network_interface = cls(
            uuid=uuid,
            private_ip=private_ip,
            mac=mac,
            rx_bytes=rx_bytes,
            rx_packets=rx_packets,
            tx_bytes=tx_bytes,
            tx_packets=tx_packets,
        )

        instance_network_interface.additional_properties = d
        return instance_network_interface

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
