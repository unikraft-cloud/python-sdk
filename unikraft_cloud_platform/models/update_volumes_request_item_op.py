from typing import Literal, cast

UpdateVolumesRequestItemOp = Literal["add", "del", "set"]

UPDATE_VOLUMES_REQUEST_ITEM_OP_VALUES: set[UpdateVolumesRequestItemOp] = {
    "add",
    "del",
    "set",
}


def check_update_volumes_request_item_op(value: str) -> UpdateVolumesRequestItemOp:
    if value in UPDATE_VOLUMES_REQUEST_ITEM_OP_VALUES:
        return cast(UpdateVolumesRequestItemOp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_VOLUMES_REQUEST_ITEM_OP_VALUES!r}")
