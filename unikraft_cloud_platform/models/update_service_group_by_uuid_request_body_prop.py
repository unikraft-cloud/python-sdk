from typing import Literal, cast

UpdateServiceGroupByUUIDRequestBodyProp = Literal["domains", "hard_limit", "services", "soft_limit"]

UPDATE_SERVICE_GROUP_BY_UUID_REQUEST_BODY_PROP_VALUES: set[UpdateServiceGroupByUUIDRequestBodyProp] = {
    "domains",
    "hard_limit",
    "services",
    "soft_limit",
}


def check_update_service_group_by_uuid_request_body_prop(value: str) -> UpdateServiceGroupByUUIDRequestBodyProp:
    if value in UPDATE_SERVICE_GROUP_BY_UUID_REQUEST_BODY_PROP_VALUES:
        return cast(UpdateServiceGroupByUUIDRequestBodyProp, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {UPDATE_SERVICE_GROUP_BY_UUID_REQUEST_BODY_PROP_VALUES!r}"
    )
