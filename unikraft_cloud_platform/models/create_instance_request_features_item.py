from typing import Literal, cast

CreateInstanceRequestFeaturesItem = Literal["delete_on_stop"]

CREATE_INSTANCE_REQUEST_FEATURES_ITEM_VALUES: set[CreateInstanceRequestFeaturesItem] = {
    "delete_on_stop",
}


def check_create_instance_request_features_item(value: str) -> CreateInstanceRequestFeaturesItem:
    if value in CREATE_INSTANCE_REQUEST_FEATURES_ITEM_VALUES:
        return cast(CreateInstanceRequestFeaturesItem, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CREATE_INSTANCE_REQUEST_FEATURES_ITEM_VALUES!r}")
