from typing import Literal, cast

UpdateServiceGroupsRequestItemOp = Literal["add", "del", "set"]

UPDATE_SERVICE_GROUPS_REQUEST_ITEM_OP_VALUES: set[UpdateServiceGroupsRequestItemOp] = {
    "add",
    "del",
    "set",
}


def check_update_service_groups_request_item_op(value: str) -> UpdateServiceGroupsRequestItemOp:
    if value in UPDATE_SERVICE_GROUPS_REQUEST_ITEM_OP_VALUES:
        return cast(UpdateServiceGroupsRequestItemOp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_SERVICE_GROUPS_REQUEST_ITEM_OP_VALUES!r}")
