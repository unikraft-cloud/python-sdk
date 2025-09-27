from typing import Literal, cast

UpdateInstancesRequestOp = Literal["add", "del", "set"]

UPDATE_INSTANCES_REQUEST_OP_VALUES: set[UpdateInstancesRequestOp] = {
    "add",
    "del",
    "set",
}


def check_update_instances_request_op(value: str) -> UpdateInstancesRequestOp:
    if value in UPDATE_INSTANCES_REQUEST_OP_VALUES:
        return cast(UpdateInstancesRequestOp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_INSTANCES_REQUEST_OP_VALUES!r}")
