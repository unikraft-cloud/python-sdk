from typing import Literal, cast

UpdateInstanceByUUIDRequestBodyOp = Literal["add", "del", "set"]

UPDATE_INSTANCE_BY_UUID_REQUEST_BODY_OP_VALUES: set[UpdateInstanceByUUIDRequestBodyOp] = {
    "add",
    "del",
    "set",
}


def check_update_instance_by_uuid_request_body_op(value: str) -> UpdateInstanceByUUIDRequestBodyOp:
    if value in UPDATE_INSTANCE_BY_UUID_REQUEST_BODY_OP_VALUES:
        return cast(UpdateInstanceByUUIDRequestBodyOp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_INSTANCE_BY_UUID_REQUEST_BODY_OP_VALUES!r}")
