import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.image_labels import ImageLabels
    from ..models.object_ import Object


T = TypeVar("T", bound="Image")


@_attrs_define
class Image:
    tag: Union[Unset, str] = UNSET
    """ The canonical name of the image is known as the "tag". """
    digest: Union[Unset, str] = UNSET
    """ The digest of the image is a unique identifier of the image manifest which
    is a string representation including the hashing algorithm and the hash
    value separated by a colon. """
    description: Union[Unset, str] = UNSET
    """ A description of the image. """
    created_at: Union[Unset, datetime.datetime] = UNSET
    """ When the image was created. """
    arch: Union[Unset, str] = UNSET
    """ The architecture of the image. """
    entrypoint: Union[Unset, list[str]] = UNSET
    """ The entrypoint of the image is the command that is run when the image is
    started. """
    cmd: Union[Unset, list[str]] = UNSET
    """ The command to run when the image is started. """
    env: Union[Unset, list[str]] = UNSET
    """ The environment variables to set when the image is started. """
    ports: Union[Unset, list[str]] = UNSET
    """ Documented port mappings for the image. """
    volumes: Union[Unset, list[str]] = UNSET
    """ Documented volumes for the image. """
    labels: Union[Unset, "ImageLabels"] = UNSET
    """ Labels are key-value pairs. """
    workdir: Union[Unset, str] = UNSET
    """ The working directory for the image is the directory that is set as the
    current working directory when the image is started. """
    kernel: Union[Unset, "Object"] = UNSET
    """ An object is a single component of an image which is external and can be
    uniquely identified by its digest. """
    auxiliary_roms: Union[Unset, list["Object"]] = UNSET
    """ List of auxiliary ROMs that are used by the image. """
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        tag = self.tag

        digest = self.digest

        description = self.description

        created_at: Union[Unset, str] = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        arch = self.arch

        entrypoint: Union[Unset, list[str]] = UNSET
        if not isinstance(self.entrypoint, Unset):
            entrypoint = self.entrypoint

        cmd: Union[Unset, list[str]] = UNSET
        if not isinstance(self.cmd, Unset):
            cmd = self.cmd

        env: Union[Unset, list[str]] = UNSET
        if not isinstance(self.env, Unset):
            env = self.env

        ports: Union[Unset, list[str]] = UNSET
        if not isinstance(self.ports, Unset):
            ports = self.ports

        volumes: Union[Unset, list[str]] = UNSET
        if not isinstance(self.volumes, Unset):
            volumes = self.volumes

        labels: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.labels, Unset):
            labels = self.labels.to_dict()

        workdir = self.workdir

        kernel: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.kernel, Unset):
            kernel = self.kernel.to_dict()

        auxiliary_roms: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.auxiliary_roms, Unset):
            auxiliary_roms = []
            for auxiliary_roms_item_data in self.auxiliary_roms:
                auxiliary_roms_item = auxiliary_roms_item_data.to_dict()
                auxiliary_roms.append(auxiliary_roms_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if tag is not UNSET:
            field_dict["tag"] = tag
        if digest is not UNSET:
            field_dict["digest"] = digest
        if description is not UNSET:
            field_dict["description"] = description
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if arch is not UNSET:
            field_dict["arch"] = arch
        if entrypoint is not UNSET:
            field_dict["entrypoint"] = entrypoint
        if cmd is not UNSET:
            field_dict["cmd"] = cmd
        if env is not UNSET:
            field_dict["env"] = env
        if ports is not UNSET:
            field_dict["ports"] = ports
        if volumes is not UNSET:
            field_dict["volumes"] = volumes
        if labels is not UNSET:
            field_dict["labels"] = labels
        if workdir is not UNSET:
            field_dict["workdir"] = workdir
        if kernel is not UNSET:
            field_dict["kernel"] = kernel
        if auxiliary_roms is not UNSET:
            field_dict["auxiliary_roms"] = auxiliary_roms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.image_labels import ImageLabels
        from ..models.object_ import Object

        d = dict(src_dict)
        tag = d.pop("tag", UNSET)

        digest = d.pop("digest", UNSET)

        description = d.pop("description", UNSET)

        _created_at = d.pop("created_at", UNSET)
        created_at: Union[Unset, datetime.datetime]
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        arch = d.pop("arch", UNSET)

        entrypoint = cast(list[str], d.pop("entrypoint", UNSET))

        cmd = cast(list[str], d.pop("cmd", UNSET))

        env = cast(list[str], d.pop("env", UNSET))

        ports = cast(list[str], d.pop("ports", UNSET))

        volumes = cast(list[str], d.pop("volumes", UNSET))

        _labels = d.pop("labels", UNSET)
        labels: Union[Unset, ImageLabels]
        if isinstance(_labels, Unset):
            labels = UNSET
        else:
            labels = ImageLabels.from_dict(_labels)

        workdir = d.pop("workdir", UNSET)

        _kernel = d.pop("kernel", UNSET)
        kernel: Union[Unset, Object]
        if isinstance(_kernel, Unset):
            kernel = UNSET
        else:
            kernel = Object.from_dict(_kernel)

        auxiliary_roms = []
        _auxiliary_roms = d.pop("auxiliary_roms", UNSET)
        for auxiliary_roms_item_data in _auxiliary_roms or []:
            auxiliary_roms_item = Object.from_dict(auxiliary_roms_item_data)

            auxiliary_roms.append(auxiliary_roms_item)

        image = cls(
            tag=tag,
            digest=digest,
            description=description,
            created_at=created_at,
            arch=arch,
            entrypoint=entrypoint,
            cmd=cmd,
            env=env,
            ports=ports,
            volumes=volumes,
            labels=labels,
            workdir=workdir,
            kernel=kernel,
            auxiliary_roms=auxiliary_roms,
        )

        image.additional_properties = d
        return image

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
