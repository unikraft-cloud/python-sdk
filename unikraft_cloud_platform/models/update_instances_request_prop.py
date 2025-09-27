from typing import Literal, cast

UpdateInstancesRequestProp = Literal[
    "args", "delete_lock", "env", "image", "memory_mb", "scale_to_zero", "tags", "vcpus"
]

UPDATE_INSTANCES_REQUEST_PROP_VALUES: set[UpdateInstancesRequestProp] = {
    "args",
    "delete_lock",
    "env",
    "image",
    "memory_mb",
    "scale_to_zero",
    "tags",
    "vcpus",
}


def check_update_instances_request_prop(value: str) -> UpdateInstancesRequestProp:
    if value in UPDATE_INSTANCES_REQUEST_PROP_VALUES:
        return cast(UpdateInstancesRequestProp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_INSTANCES_REQUEST_PROP_VALUES!r}")
