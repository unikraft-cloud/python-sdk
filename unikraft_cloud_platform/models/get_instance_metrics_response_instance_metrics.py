from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetInstanceMetricsResponseInstanceMetrics")


@_attrs_define
class GetInstanceMetricsResponseInstanceMetrics:
    rss_bytes: Union[Unset, int] = UNSET
    """ Resident set size of the VMM in bytes.

    The resident set size (RSS) specifies the amount of physical memory that
    has been touched by the instance and is currently reserved for the
    instance on the Unikraft Cloud server.  The RSS grows until the instance
    has touched all memory assigned to it via the memory_mb setting and may
    also exceed this value as supporting services running outside the
    instance acquire memory.  The RSS is different from the current amount of
    memory allocated by the application, which is likely to fluctuate over
    the lifetime of the application.  The RSS is not a cumulative metric.
    When the instance is stopped rss goes down to 0. """
    cpu_time_ms: Union[Unset, int] = UNSET
    """ Consumed CPU time in milliseconds. """
    boot_time_us: Union[Unset, int] = UNSET
    """ The boot time of the instance in microseconds.  We take a pragmatic
    approach is to define the boot time.  We calculate this as the difference
    in time between the moment the virtualization toolstack is invoked to
    respond to a VM boot request and the moment the OS starts executing user
    code (i.e., the end of the guest OS boot process).  This is essentially the
    time that a user would experience in a deployment, minus the application
    initialization time, which we leave out since it is independent from the
    OS. """
    net_time_us: Union[Unset, int] = UNSET
    """ This is the time it took for the user-level application to start listening
    on a non-localhost port measured in microseconds.  This is the time from
    when the instance started until it reasonably ready to start responding to
    network requests.  This is useful for measuring the time it takes for the
    instance to become operationally ready. """
    rx_bytes: Union[Unset, int] = UNSET
    """ Total amount of bytes received from network. """
    rx_packets: Union[Unset, int] = UNSET
    """ Total count of packets received from network. """
    tx_bytes: Union[Unset, int] = UNSET
    """ Total amount of bytes transmitted over network. """
    tx_packets: Union[Unset, int] = UNSET
    """ Total count of packets transmitted over network. """
    nconns: Union[Unset, int] = UNSET
    """ Number of currently established inbound connections (non-HTTP). """
    nreqs: Union[Unset, int] = UNSET
    """ Number of in-flight HTTP requests. """
    nqueued: Union[Unset, int] = UNSET
    """ Number of queued inbound connections and HTTP requests. """
    ntotal: Union[Unset, int] = UNSET
    """ Total number of inbound connections and HTTP requests handled. """
    message: Union[Unset, str] = UNSET
    """ An optional message providing additional information about the status.
    This field is useful when the status is not `success`. """
    error: Union[Unset, int] = UNSET
    """ An optional error code providing additional information about the status.
    This field is useful when the status is not `success`. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        rss_bytes = self.rss_bytes

        cpu_time_ms = self.cpu_time_ms

        boot_time_us = self.boot_time_us

        net_time_us = self.net_time_us

        rx_bytes = self.rx_bytes

        rx_packets = self.rx_packets

        tx_bytes = self.tx_bytes

        tx_packets = self.tx_packets

        nconns = self.nconns

        nreqs = self.nreqs

        nqueued = self.nqueued

        ntotal = self.ntotal

        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if rss_bytes is not UNSET:
            field_dict["rss_bytes"] = rss_bytes
        if cpu_time_ms is not UNSET:
            field_dict["cpu_time_ms"] = cpu_time_ms
        if boot_time_us is not UNSET:
            field_dict["boot_time_us"] = boot_time_us
        if net_time_us is not UNSET:
            field_dict["net_time_us"] = net_time_us
        if rx_bytes is not UNSET:
            field_dict["rx_bytes"] = rx_bytes
        if rx_packets is not UNSET:
            field_dict["rx_packets"] = rx_packets
        if tx_bytes is not UNSET:
            field_dict["tx_bytes"] = tx_bytes
        if tx_packets is not UNSET:
            field_dict["tx_packets"] = tx_packets
        if nconns is not UNSET:
            field_dict["nconns"] = nconns
        if nreqs is not UNSET:
            field_dict["nreqs"] = nreqs
        if nqueued is not UNSET:
            field_dict["nqueued"] = nqueued
        if ntotal is not UNSET:
            field_dict["ntotal"] = ntotal
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        rss_bytes = d.pop("rss_bytes", UNSET)

        cpu_time_ms = d.pop("cpu_time_ms", UNSET)

        boot_time_us = d.pop("boot_time_us", UNSET)

        net_time_us = d.pop("net_time_us", UNSET)

        rx_bytes = d.pop("rx_bytes", UNSET)

        rx_packets = d.pop("rx_packets", UNSET)

        tx_bytes = d.pop("tx_bytes", UNSET)

        tx_packets = d.pop("tx_packets", UNSET)

        nconns = d.pop("nconns", UNSET)

        nreqs = d.pop("nreqs", UNSET)

        nqueued = d.pop("nqueued", UNSET)

        ntotal = d.pop("ntotal", UNSET)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        get_instance_metrics_response_instance_metrics = cls(
            rss_bytes=rss_bytes,
            cpu_time_ms=cpu_time_ms,
            boot_time_us=boot_time_us,
            net_time_us=net_time_us,
            rx_bytes=rx_bytes,
            rx_packets=rx_packets,
            tx_bytes=tx_bytes,
            tx_packets=tx_packets,
            nconns=nconns,
            nreqs=nreqs,
            nqueued=nqueued,
            ntotal=ntotal,
            message=message,
            error=error,
        )

        get_instance_metrics_response_instance_metrics.additional_properties = d
        return get_instance_metrics_response_instance_metrics

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
