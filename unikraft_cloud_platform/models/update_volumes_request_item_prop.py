from typing import Literal, cast

UpdateVolumesRequestItemProp = Literal["delete_lock", "quota_policy", "size_mb", "tags"]

UPDATE_VOLUMES_REQUEST_ITEM_PROP_VALUES: set[UpdateVolumesRequestItemProp] = {
    "delete_lock",
    "quota_policy",
    "size_mb",
    "tags",
}


def check_update_volumes_request_item_prop(value: str) -> UpdateVolumesRequestItemProp:
    if value in UPDATE_VOLUMES_REQUEST_ITEM_PROP_VALUES:
        return cast(UpdateVolumesRequestItemProp, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UPDATE_VOLUMES_REQUEST_ITEM_PROP_VALUES!r}")
