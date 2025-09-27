from typing import Literal, cast

UpdateServiceGroupByUUIDRequestBodyOp = Literal["add", "del", "set"]

UPDATE_SERVICE_GROUP_BY_UUID_REQUEST_BODY_OP_VALUES: set[UpdateServiceGroupByUUIDRequestBodyOp] = {
    "add",
    "del",
    "set",
}


def check_update_service_group_by_uuid_request_body_op(value: str) -> UpdateServiceGroupByUUIDRequestBodyOp:
    if value in UPDATE_SERVICE_GROUP_BY_UUID_REQUEST_BODY_OP_VALUES:
        return cast(UpdateServiceGroupByUUIDRequestBodyOp, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {UPDATE_SERVICE_GROUP_BY_UUID_REQUEST_BODY_OP_VALUES!r}"
    )
