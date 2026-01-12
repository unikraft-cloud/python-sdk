from typing import Literal, cast

UpdateInstanceByUUIDRequestBodyProp = Literal[
    "args", "delete_lock", "env", "image", "memory_mb", "scale_to_zero", "tags", "vcpus"
]

UPDATE_INSTANCE_BY_UUID_REQUEST_BODY_PROP_VALUES: set[UpdateInstanceByUUIDRequestBodyProp] = {
    "args",
    "delete_lock",
    "env",
    "image",
    "memory_mb",
    "scale_to_zero",
    "tags",
    "vcpus",
}


def check_update_instance_by_uuid_request_body_prop(value: str) -> UpdateInstanceByUUIDRequestBodyProp:
    if value in UPDATE_INSTANCE_BY_UUID_REQUEST_BODY_PROP_VALUES:
        return cast(UpdateInstanceByUUIDRequestBodyProp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_INSTANCE_BY_UUID_REQUEST_BODY_PROP_VALUES!r}")
