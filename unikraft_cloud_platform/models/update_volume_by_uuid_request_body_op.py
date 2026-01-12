from typing import Literal, cast

UpdateVolumeByUUIDRequestBodyOp = Literal["add", "del", "set"]

UPDATE_VOLUME_BY_UUID_REQUEST_BODY_OP_VALUES: set[UpdateVolumeByUUIDRequestBodyOp] = {
    "add",
    "del",
    "set",
}


def check_update_volume_by_uuid_request_body_op(value: str) -> UpdateVolumeByUUIDRequestBodyOp:
    if value in UPDATE_VOLUME_BY_UUID_REQUEST_BODY_OP_VALUES:
        return cast(UpdateVolumeByUUIDRequestBodyOp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_VOLUME_BY_UUID_REQUEST_BODY_OP_VALUES!r}")
