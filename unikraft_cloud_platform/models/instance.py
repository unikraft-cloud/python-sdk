import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.instance_restart_policy import InstanceRestartPolicy, check_instance_restart_policy
from ..models.instance_state import InstanceState, check_instance_state
from ..models.response_status import ResponseStatus, check_response_status
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.instance_env import InstanceEnv
    from ..models.instance_instance_service_group import InstanceInstanceServiceGroup
    from ..models.instance_instance_volume import InstanceInstanceVolume
    from ..models.instance_network_interface import InstanceNetworkInterface
    from ..models.instance_scale_to_zero import InstanceScaleToZero


T = TypeVar("T", bound="Instance")


@_attrs_define
class Instance:
    """An instance is a unikernel virtual machine running an application."""

    uuid: Union[Unset, UUID] = UNSET
    """ The UUID of the instance.

    This is a unique identifier for the instance that is generated when the
    instance is created.  The UUID is used to reference the instance in API
    calls and can be used to identify the instance in all API calls that
    require an instance identifier. """
    name: Union[Unset, str] = UNSET
    """ The name of the instance.

    This is a human-readable name that can be used to identify the instance.
    The name must be unique within the context of your account.  The name can
    also be used to identify the instance in API calls. """
    created_at: Union[Unset, datetime.datetime] = UNSET
    """ The time the instance was created. """
    state: Union[Unset, InstanceState] = UNSET
    """ The state of the instance.  This indicates the current state of the
    instance, such as whether it is running, stopped, or in an error state. """
    private_fqdn: Union[Unset, str] = UNSET
    """ The internal hostname of the instance.  This address can be used privately
    within the Unikraft Cloud network to access the instance.  It is not
    accessible from the public Internet. """
    image: Union[Unset, str] = UNSET
    """ The image used to create the instance.  This is a reference to the
    Unikraft image that was used to create the instance. """
    memory_mb: Union[Unset, int] = UNSET
    """ The amount of memory in megabytes allocated for the instance.  This is the
    total amount of memory that is available to the instance for its
    operations. """
    vcpus: Union[Unset, int] = UNSET
    """ The number of vCPUs allocated for the instance.  This is the total
    number of virtual CPUs that are available to the instance for its
    operations. """
    args: Union[Unset, list[str]] = UNSET
    """ The arguments passed to the instance when it was started.  This is a
    list of command-line arguments that were provided to the instance at
    startup.  These arguments can be used to configure the behavior of the
    instance and its applications. """
    env: Union[Unset, "InstanceEnv"] = UNSET
    """ Environment variables set for the instance. """
    start_count: Union[Unset, int] = UNSET
    """ The total number of times the instance has been started.  This is a counter
    that increments each time the instance is started, regardless of whether it
    was manually stopped or restarted.  This can be useful for tracking the
    usage of the instance over time and/or for debugging purposes. """
    restart_count: Union[Unset, int] = UNSET
    """ The total number of times the instance has been restarted. This is a counter
    that increments each time the instance has been restarted. This can be
    useful for tracking the usage of the instance over time and/or for
    debugging purposes. """
    started_at: Union[Unset, datetime.datetime] = UNSET
    """ The time the instance was started.  This is the timestamp when the
    instance was last started. """
    stopped_at: Union[Unset, datetime.datetime] = UNSET
    """ The time the instance was stopped.  This is the timestamp when the
    instance was last stopped.  If the instance is currently running, this
    field will be empty. """
    uptime_ms: Union[Unset, int] = UNSET
    """ The total amount of time the instance has been running in milliseconds. """
    vmm_start_time_us: Union[Unset, int] = UNSET
    """ (Developer-only).  The time taken between the main controller and the
    beginning of execution of the VMM (Virtual Machine Monitor) measured in
    microseconds.  This field is primarily used for debugging and performance
    analysis purposes. """
    vmm_load_time_us: Union[Unset, int] = UNSET
    """ (Developer-only).  The time it took the VMM (Virtual Machine Monitor) to
    load the instance's kernel and initramfs into VM memory measured in
    microseconds.  This field is primarily used for debugging and performance
    analysis purposes. """
    vmm_ready_time_us: Union[Unset, int] = UNSET
    """ (Developer-only).  The time taken for the VMM (Virtual Machine Monitor) to
    become ready to execute the instance measured in microseconds.  This is the
    time from when the VMM started until it was ready to execute the instance's
    code.  This field is primarily used for debugging and performance analysis
    purposes. """
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
    stop_reason: Union[Unset, int] = UNSET
    """ The instance stop reason.

    Provides reason as to why an instance is stopped or in the process of
    shutting down.  The stop reason is a bitmask that tells you the origin of
    the shutdown:

    | Bit     | 4          | 3          | 2          | 1          | 0 (LSB)      |
    |---------|------------|------------|------------|------------|--------------|
    | Purpose | [F]orced   | [U]ser     | [P]latform | [A]pp      | [K]ernel     |

    - **Forced**:   This was a force stop.  A forced stop does not give the
                    instance a chance to perform a clean shutdown.  Bits 0
                    (Kernel) and 1 (App) can thus never be set for forced
                    shutdowns.  Consequently, there won't be an `exit_code` or
                    `stop_code`.
    - **User**:     Stop initiated by user, e.g. via an API call.
    - **Platform**: Stop initiated by platform, e.g. an autoscale policy.
    - **App**:      The Application exited.  The `exit_code` field will be set.
    - **Kernel**:   The kernel exited.  The `stop_code` field will be set.

    For example, the stop reason will contain the following values in the given
    scenarios:

    | Value | Bitmask | Aliases | Scenario |
    |-------|---------|---------|----------|
    | 28    | `11100` | `FUP--` | Forced user-initiated shutdown. |
    | 15    | `01111` | `-UPAK` | Regular user-initiated shutdown. The application and kernel have exited. The
    exit_code and stop_code indicate if the application and kernel shut down cleanly. |
    | 13    | `01101` | `-UP-K` | The user initiated a shutdown but the application was forcefully killed by the
    kernel during shutdown. This can be the case if the image does not support a clean application exit or the
    application crashed after receiving a termination signal. The exit_code won’t be present in this scenario. |
    | 7     | `00111` | `--PAK` | Unikraft Cloud initiated the shutdown, for example, due to scale-to-zero. The
    application and kernel have exited. The exit_code and stop_code indicate if the application and kernel shut down
    cleanly. |
    | 3     | `00011` | `---AK` | The application exited. The exit_code and stop_code indicate if the application
    and kernel shut down cleanly. |
    | 1     | `00001` | `----K` | The instance likely expierenced a fatal crash and the stop_code contains more
    information about the cause of the crash. |
    | 0     | `00000` | `-----` | The stop reason is unknown. | """
    exit_code: Union[Unset, int] = UNSET
    """ The application exit code.

    This is the code which the application returns upon leaving its main entry
    point.  The encoding of the exit code is application specific.  See the
    documentation of the application for more details.  Usually, an exit code
    of `0` indicates success / no failure. """
    stop_code: Union[Unset, int] = UNSET
    """ The kernel stop code.

    This value encodes multiple details about the stop irrespective of the
    application.

    ```
    MSB                                                     LSB
    ┌──────────────┬──────────┬──────────┬───────────┬────────┐
    │ 31 ────── 24 │ 23 ── 16 │    15    │ 14 ──── 8 │ 7 ── 0 │
    ├──────────────┼──────────┼──────────┼───────────┼────────┤
    │ reserved[^1] │ errno    │ shutdown │ initlevel │ reason │
    └──────────────┴──────────┴──────────┴───────────┴────────┘
    ```

    - **errno**:     The application errno, using Linux's errno.h values.
                     (Optional, can be 0.)
    - **shutdown**:  Whether the shutdown originated from the inittable (0) or
                     from the termtable (1).
    - **initlevel**: The initlevel at the time of the stop.
    - **reason**:    The reason for the stop.  See `StopCodeReason`.

    [^1]: Reserved for future use. """
    restart_policy: Union[Unset, InstanceRestartPolicy] = UNSET
    """ The restart configuration for the instance.

    When an instance stops either because the application exits or the instance
    crashes, Unikraft Cloud can auto-restart your instance.  Auto-restarts are
    performed according to the restart policy configured for a particular
    instance.

    The policy can have the following values:

    | Policy       | Description |
    |--------------|-------------|
    | `never`      | Never restart the instance (default). |
    | `always`     | Always restart the instance when the stop is initiated from within the instance (i.e., the
    application exits or the instance crashes). |
    | `on-failure` | Only restart the instance if it crashes. |

    When an instance stops, the stop reason and the configured restart policy
    are evaluated to decide if a restart should be performed.  Unikraft Cloud
    uses an exponential back-off delay (immediate, 5s, 10s, 20s, 40s, ..., 5m)
    to slow down restarts in tight crash loops.  If an instance runs without
    problems for 10s the back-off delay is reset and the restart sequence ends.

    The `restart.attempt` attribute reported in counts the number of restarts
    performed in the current sequence.  The `restart.next_at` field indicates
    when the next restart will take place if a back-off delay is in effect.

    A manual start or stop of the instance aborts the restart sequence and
    resets the back-off delay. """
    scale_to_zero: Union[Unset, "InstanceScaleToZero"] = UNSET
    """ Scale-to-zero defines the configuration for scaling the instance to zero.
    When an instance is scaled-to-zero it can be either stopped (and fully
    shutdown) or paused wherein the state of the instance is preserved (e.g., RAM
    contents) and the instance can be resumed later without losing its state,
    i.e. "stateful". """
    volumes: Union[Unset, list["InstanceInstanceVolume"]] = UNSET
    """ The list of volumes attached to the instance. """
    service_group: Union[Unset, "InstanceInstanceServiceGroup"] = UNSET
    """ The service group configuration for the instance.

    This is a reference to the service group that the instance is part of.  The
    service group defines the services (e.g. ports, connection handling) that
    the instance exposes and how they are configured. """
    network_interfaces: Union[Unset, list["InstanceNetworkInterface"]] = UNSET
    """ The network interfaces of the instance. """
    tags: Union[Unset, list[str]] = UNSET
    """ The tags associated with the instance. """
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

        state: Union[Unset, str] = UNSET
        if not isinstance(self.state, Unset):
            state = self.state

        private_fqdn = self.private_fqdn

        image = self.image

        memory_mb = self.memory_mb

        vcpus = self.vcpus

        args: Union[Unset, list[str]] = UNSET
        if not isinstance(self.args, Unset):
            args = self.args

        env: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.env, Unset):
            env = self.env.to_dict()

        start_count = self.start_count

        restart_count = self.restart_count

        started_at: Union[Unset, str] = UNSET
        if not isinstance(self.started_at, Unset):
            started_at = self.started_at.isoformat()

        stopped_at: Union[Unset, str] = UNSET
        if not isinstance(self.stopped_at, Unset):
            stopped_at = self.stopped_at.isoformat()

        uptime_ms = self.uptime_ms

        vmm_start_time_us = self.vmm_start_time_us

        vmm_load_time_us = self.vmm_load_time_us

        vmm_ready_time_us = self.vmm_ready_time_us

        boot_time_us = self.boot_time_us

        net_time_us = self.net_time_us

        stop_reason = self.stop_reason

        exit_code = self.exit_code

        stop_code = self.stop_code

        restart_policy: Union[Unset, str] = UNSET
        if not isinstance(self.restart_policy, Unset):
            restart_policy = self.restart_policy

        scale_to_zero: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.scale_to_zero, Unset):
            scale_to_zero = self.scale_to_zero.to_dict()

        volumes: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.volumes, Unset):
            volumes = []
            for volumes_item_data in self.volumes:
                volumes_item = volumes_item_data.to_dict()
                volumes.append(volumes_item)

        service_group: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.service_group, Unset):
            service_group = self.service_group.to_dict()

        network_interfaces: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.network_interfaces, Unset):
            network_interfaces = []
            for network_interfaces_item_data in self.network_interfaces:
                network_interfaces_item = network_interfaces_item_data.to_dict()
                network_interfaces.append(network_interfaces_item)

        tags: Union[Unset, list[str]] = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags

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
        if state is not UNSET:
            field_dict["state"] = state
        if private_fqdn is not UNSET:
            field_dict["private_fqdn"] = private_fqdn
        if image is not UNSET:
            field_dict["image"] = image
        if memory_mb is not UNSET:
            field_dict["memory_mb"] = memory_mb
        if vcpus is not UNSET:
            field_dict["vcpus"] = vcpus
        if args is not UNSET:
            field_dict["args"] = args
        if env is not UNSET:
            field_dict["env"] = env
        if start_count is not UNSET:
            field_dict["start_count"] = start_count
        if restart_count is not UNSET:
            field_dict["restart_count"] = restart_count
        if started_at is not UNSET:
            field_dict["started_at"] = started_at
        if stopped_at is not UNSET:
            field_dict["stopped_at"] = stopped_at
        if uptime_ms is not UNSET:
            field_dict["uptime_ms"] = uptime_ms
        if vmm_start_time_us is not UNSET:
            field_dict["vmm_start_time_us"] = vmm_start_time_us
        if vmm_load_time_us is not UNSET:
            field_dict["vmm_load_time_us"] = vmm_load_time_us
        if vmm_ready_time_us is not UNSET:
            field_dict["vmm_ready_time_us"] = vmm_ready_time_us
        if boot_time_us is not UNSET:
            field_dict["boot_time_us"] = boot_time_us
        if net_time_us is not UNSET:
            field_dict["net_time_us"] = net_time_us
        if stop_reason is not UNSET:
            field_dict["stop_reason"] = stop_reason
        if exit_code is not UNSET:
            field_dict["exit_code"] = exit_code
        if stop_code is not UNSET:
            field_dict["stop_code"] = stop_code
        if restart_policy is not UNSET:
            field_dict["restart_policy"] = restart_policy
        if scale_to_zero is not UNSET:
            field_dict["scale_to_zero"] = scale_to_zero
        if volumes is not UNSET:
            field_dict["volumes"] = volumes
        if service_group is not UNSET:
            field_dict["service_group"] = service_group
        if network_interfaces is not UNSET:
            field_dict["network_interfaces"] = network_interfaces
        if tags is not UNSET:
            field_dict["tags"] = tags
        if status is not UNSET:
            field_dict["status"] = status
        if message is not UNSET:
            field_dict["message"] = message
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.instance_env import InstanceEnv
        from ..models.instance_instance_service_group import InstanceInstanceServiceGroup
        from ..models.instance_instance_volume import InstanceInstanceVolume
        from ..models.instance_network_interface import InstanceNetworkInterface
        from ..models.instance_scale_to_zero import InstanceScaleToZero

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

        _state = d.pop("state", UNSET)
        state: Union[Unset, InstanceState]
        if isinstance(_state, Unset):
            state = UNSET
        else:
            state = check_instance_state(_state)

        private_fqdn = d.pop("private_fqdn", UNSET)

        image = d.pop("image", UNSET)

        memory_mb = d.pop("memory_mb", UNSET)

        vcpus = d.pop("vcpus", UNSET)

        args = cast(list[str], d.pop("args", UNSET))

        _env = d.pop("env", UNSET)
        env: Union[Unset, InstanceEnv]
        if isinstance(_env, Unset):
            env = UNSET
        else:
            env = InstanceEnv.from_dict(_env)

        start_count = d.pop("start_count", UNSET)

        restart_count = d.pop("restart_count", UNSET)

        _started_at = d.pop("started_at", UNSET)
        started_at: Union[Unset, datetime.datetime]
        if isinstance(_started_at, Unset):
            started_at = UNSET
        else:
            started_at = isoparse(_started_at)

        _stopped_at = d.pop("stopped_at", UNSET)
        stopped_at: Union[Unset, datetime.datetime]
        if isinstance(_stopped_at, Unset):
            stopped_at = UNSET
        else:
            stopped_at = isoparse(_stopped_at)

        uptime_ms = d.pop("uptime_ms", UNSET)

        vmm_start_time_us = d.pop("vmm_start_time_us", UNSET)

        vmm_load_time_us = d.pop("vmm_load_time_us", UNSET)

        vmm_ready_time_us = d.pop("vmm_ready_time_us", UNSET)

        boot_time_us = d.pop("boot_time_us", UNSET)

        net_time_us = d.pop("net_time_us", UNSET)

        stop_reason = d.pop("stop_reason", UNSET)

        exit_code = d.pop("exit_code", UNSET)

        stop_code = d.pop("stop_code", UNSET)

        _restart_policy = d.pop("restart_policy", UNSET)
        restart_policy: Union[Unset, InstanceRestartPolicy]
        if isinstance(_restart_policy, Unset):
            restart_policy = UNSET
        else:
            restart_policy = check_instance_restart_policy(_restart_policy)

        _scale_to_zero = d.pop("scale_to_zero", UNSET)
        scale_to_zero: Union[Unset, InstanceScaleToZero]
        if isinstance(_scale_to_zero, Unset):
            scale_to_zero = UNSET
        else:
            scale_to_zero = InstanceScaleToZero.from_dict(_scale_to_zero)

        volumes = []
        _volumes = d.pop("volumes", UNSET)
        for volumes_item_data in _volumes or []:
            volumes_item = InstanceInstanceVolume.from_dict(volumes_item_data)

            volumes.append(volumes_item)

        _service_group = d.pop("service_group", UNSET)
        service_group: Union[Unset, InstanceInstanceServiceGroup]
        if isinstance(_service_group, Unset):
            service_group = UNSET
        else:
            service_group = InstanceInstanceServiceGroup.from_dict(_service_group)

        network_interfaces = []
        _network_interfaces = d.pop("network_interfaces", UNSET)
        for network_interfaces_item_data in _network_interfaces or []:
            network_interfaces_item = InstanceNetworkInterface.from_dict(network_interfaces_item_data)

            network_interfaces.append(network_interfaces_item)

        tags = cast(list[str], d.pop("tags", UNSET))

        _status = d.pop("status", UNSET)
        status: Union[Unset, ResponseStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = check_response_status(_status)

        message = d.pop("message", UNSET)

        error = d.pop("error", UNSET)

        instance = cls(
            uuid=uuid,
            name=name,
            created_at=created_at,
            state=state,
            private_fqdn=private_fqdn,
            image=image,
            memory_mb=memory_mb,
            vcpus=vcpus,
            args=args,
            env=env,
            start_count=start_count,
            restart_count=restart_count,
            started_at=started_at,
            stopped_at=stopped_at,
            uptime_ms=uptime_ms,
            vmm_start_time_us=vmm_start_time_us,
            vmm_load_time_us=vmm_load_time_us,
            vmm_ready_time_us=vmm_ready_time_us,
            boot_time_us=boot_time_us,
            net_time_us=net_time_us,
            stop_reason=stop_reason,
            exit_code=exit_code,
            stop_code=stop_code,
            restart_policy=restart_policy,
            scale_to_zero=scale_to_zero,
            volumes=volumes,
            service_group=service_group,
            network_interfaces=network_interfaces,
            tags=tags,
            status=status,
            message=message,
            error=error,
        )

        instance.additional_properties = d
        return instance

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
