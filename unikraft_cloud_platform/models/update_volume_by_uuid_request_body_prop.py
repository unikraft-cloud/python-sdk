from typing import Literal, cast

UpdateVolumeByUUIDRequestBodyProp = Literal["delete_lock", "quota_policy", "size_mb", "tags"]

UPDATE_VOLUME_BY_UUID_REQUEST_BODY_PROP_VALUES: set[UpdateVolumeByUUIDRequestBodyProp] = {
    "delete_lock",
    "quota_policy",
    "size_mb",
    "tags",
}


def check_update_volume_by_uuid_request_body_prop(value: str) -> UpdateVolumeByUUIDRequestBodyProp:
    if value in UPDATE_VOLUME_BY_UUID_REQUEST_BODY_PROP_VALUES:
        return cast(UpdateVolumeByUUIDRequestBodyProp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_VOLUME_BY_UUID_REQUEST_BODY_PROP_VALUES!r}")
