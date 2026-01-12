from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.create_instance_request_features_item import (
    CreateInstanceRequestFeaturesItem,
    check_create_instance_request_features_item,
)
from ..models.create_instance_request_restart_policy import (
    CreateInstanceRequestRestartPolicy,
    check_create_instance_request_restart_policy,
)
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_instance_request_env import CreateInstanceRequestEnv
    from ..models.create_instance_request_service_group import CreateInstanceRequestServiceGroup
    from ..models.create_instance_request_volume import CreateInstanceRequestVolume
    from ..models.instance_scale_to_zero import InstanceScaleToZero


T = TypeVar("T", bound="CreateInstanceRequest")


@_attrs_define
class CreateInstanceRequest:
    """The request message for creating a new instance."""

    image: str
    """ The image to use for the instance. """
    name: Union[Unset, str] = UNSET
    """ (Optional).  The name of the instance.

    If not provided, a random name will be generated.  The name must be unique. """
    args: Union[Unset, list[str]] = UNSET
    """ (Optional).  The arguments to pass to the instance when it starts. """
    env: Union[Unset, "CreateInstanceRequestEnv"] = UNSET
    """ (Optional).  Environment variables to set for the instance. """
    memory_mb: Union[Unset, int] = UNSET
    """ (Optional).  Memory in MB to allocate for the instance.  Default is 128. """
    service_group: Union[Unset, "CreateInstanceRequestServiceGroup"] = UNSET
    """ The service group configuration when creating an instance.

    If no existing (persistent) service group is specified via its identifier,
    a new (ephemeral) service group can be created by specifying the services
    it should expose.  A service defines the configuration settings of an
    exposed port by the instance.  A service is a combination of a public port,
    an internal port, and a set of handlers that define how the service will
    handle incoming connections. """
    volumes: Union[Unset, list["CreateInstanceRequestVolume"]] = UNSET
    """ Volumes to attach to the instance.

    This list can contain both existing and new volumes to create as part of
    the instance creation.  Existing volumes can be referenced by their name or
    UUID.  New volumes can be created by specifying a name, size in MiB, and
    mount point in the instance.  The mount point is the directory in the
    instance where the volume will be mounted. """
    autostart: Union[Unset, bool] = UNSET
    """ Whether the instance should start automatically on creation. """
    replicas: Union[Unset, int] = UNSET
    """ Number of replicas for the instance. """
    restart_policy: Union[Unset, CreateInstanceRequestRestartPolicy] = UNSET
    """ Restart policy for the instance.  This defines how the instance should
    behave when it stops or crashes. """
    scale_to_zero: Union[Unset, "InstanceScaleToZero"] = UNSET
    """ Scale-to-zero defines the configuration for scaling the instance to zero.
    When an instance is scaled-to-zero it can be either stopped (and fully
    shutdown) or paused wherein the state of the instance is preserved (e.g., RAM
    contents) and the instance can be resumed later without losing its state,
    i.e. "stateful". """
    vcpus: Union[Unset, int] = UNSET
    """ Number of vCPUs to allocate for the instance. """
    wait_timeout_ms: Union[Unset, int] = UNSET
    """ Timeout to wait for all new instances to reach running state in
    milliseconds.  If you autostart your new instance, you can wait for it to
    finish starting with a blocking API call if you specify a wait timeout
    greater than zero.  No wait performed for a value of 0. """
    features: Union[Unset, list[CreateInstanceRequestFeaturesItem]] = UNSET
    """ Features to enable for the instance.  Features are specific
    configurations or capabilities that can be enabled for the instance. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        image = self.image

        name = self.name

        args: Union[Unset, list[str]] = UNSET
        if not isinstance(self.args, Unset):
            args = self.args

        env: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.env, Unset):
            env = self.env.to_dict()

        memory_mb = self.memory_mb

        service_group: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.service_group, Unset):
            service_group = self.service_group.to_dict()

        volumes: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.volumes, Unset):
            volumes = []
            for volumes_item_data in self.volumes:
                volumes_item = volumes_item_data.to_dict()
                volumes.append(volumes_item)

        autostart = self.autostart

        replicas = self.replicas

        restart_policy: Union[Unset, str] = UNSET
        if not isinstance(self.restart_policy, Unset):
            restart_policy = self.restart_policy

        scale_to_zero: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.scale_to_zero, Unset):
            scale_to_zero = self.scale_to_zero.to_dict()

        vcpus = self.vcpus

        wait_timeout_ms = self.wait_timeout_ms

        features: Union[Unset, list[str]] = UNSET
        if not isinstance(self.features, Unset):
            features = []
            for features_item_data in self.features:
                features_item: str = features_item_data
                features.append(features_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "image": image,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name
        if args is not UNSET:
            field_dict["args"] = args
        if env is not UNSET:
            field_dict["env"] = env
        if memory_mb is not UNSET:
            field_dict["memory_mb"] = memory_mb
        if service_group is not UNSET:
            field_dict["service_group"] = service_group
        if volumes is not UNSET:
            field_dict["volumes"] = volumes
        if autostart is not UNSET:
            field_dict["autostart"] = autostart
        if replicas is not UNSET:
            field_dict["replicas"] = replicas
        if restart_policy is not UNSET:
            field_dict["restart_policy"] = restart_policy
        if scale_to_zero is not UNSET:
            field_dict["scale_to_zero"] = scale_to_zero
        if vcpus is not UNSET:
            field_dict["vcpus"] = vcpus
        if wait_timeout_ms is not UNSET:
            field_dict["wait_timeout_ms"] = wait_timeout_ms
        if features is not UNSET:
            field_dict["features"] = features

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_instance_request_env import CreateInstanceRequestEnv
        from ..models.create_instance_request_service_group import CreateInstanceRequestServiceGroup
        from ..models.create_instance_request_volume import CreateInstanceRequestVolume
        from ..models.instance_scale_to_zero import InstanceScaleToZero

        d = dict(src_dict)
        image = d.pop("image")

        name = d.pop("name", UNSET)

        args = cast(list[str], d.pop("args", UNSET))

        _env = d.pop("env", UNSET)
        env: Union[Unset, CreateInstanceRequestEnv]
        if isinstance(_env, Unset):
            env = UNSET
        else:
            env = CreateInstanceRequestEnv.from_dict(_env)

        memory_mb = d.pop("memory_mb", UNSET)

        _service_group = d.pop("service_group", UNSET)
        service_group: Union[Unset, CreateInstanceRequestServiceGroup]
        if isinstance(_service_group, Unset):
            service_group = UNSET
        else:
            service_group = CreateInstanceRequestServiceGroup.from_dict(_service_group)

        volumes = []
        _volumes = d.pop("volumes", UNSET)
        for volumes_item_data in _volumes or []:
            volumes_item = CreateInstanceRequestVolume.from_dict(volumes_item_data)

            volumes.append(volumes_item)

        autostart = d.pop("autostart", UNSET)

        replicas = d.pop("replicas", UNSET)

        _restart_policy = d.pop("restart_policy", UNSET)
        restart_policy: Union[Unset, CreateInstanceRequestRestartPolicy]
        if isinstance(_restart_policy, Unset):
            restart_policy = UNSET
        else:
            restart_policy = check_create_instance_request_restart_policy(_restart_policy)

        _scale_to_zero = d.pop("scale_to_zero", UNSET)
        scale_to_zero: Union[Unset, InstanceScaleToZero]
        if isinstance(_scale_to_zero, Unset):
            scale_to_zero = UNSET
        else:
            scale_to_zero = InstanceScaleToZero.from_dict(_scale_to_zero)

        vcpus = d.pop("vcpus", UNSET)

        wait_timeout_ms = d.pop("wait_timeout_ms", UNSET)

        features = []
        _features = d.pop("features", UNSET)
        for features_item_data in _features or []:
            features_item = check_create_instance_request_features_item(features_item_data)

            features.append(features_item)

        create_instance_request = cls(
            image=image,
            name=name,
            args=args,
            env=env,
            memory_mb=memory_mb,
            service_group=service_group,
            volumes=volumes,
            autostart=autostart,
            replicas=replicas,
            restart_policy=restart_policy,
            scale_to_zero=scale_to_zero,
            vcpus=vcpus,
            wait_timeout_ms=wait_timeout_ms,
            features=features,
        )

        create_instance_request.additional_properties = d
        return create_instance_request

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
