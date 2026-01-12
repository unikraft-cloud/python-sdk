from typing import Literal, cast

UpdateServiceGroupsRequestItemProp = Literal["domains", "hard_limit", "services", "soft_limit"]

UPDATE_SERVICE_GROUPS_REQUEST_ITEM_PROP_VALUES: set[UpdateServiceGroupsRequestItemProp] = {
    "domains",
    "hard_limit",
    "services",
    "soft_limit",
}


def check_update_service_groups_request_item_prop(value: str) -> UpdateServiceGroupsRequestItemProp:
    if value in UPDATE_SERVICE_GROUPS_REQUEST_ITEM_PROP_VALUES:
        return cast(UpdateServiceGroupsRequestItemProp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_SERVICE_GROUPS_REQUEST_ITEM_PROP_VALUES!r}")
