from typing import Literal, cast

WaitInstanceByUUIDRequestBodyState = Literal["draining", "running", "standby", "starting", "stopped", "stopping"]

WAIT_INSTANCE_BY_UUID_REQUEST_BODY_STATE_VALUES: set[WaitInstanceByUUIDRequestBodyState] = {
    "draining",
    "running",
    "standby",
    "starting",
    "stopped",
    "stopping",
}


def check_wait_instance_by_uuid_request_body_state(value: str) -> WaitInstanceByUUIDRequestBodyState:
    if value in WAIT_INSTANCE_BY_UUID_REQUEST_BODY_STATE_VALUES:
        return cast(WaitInstanceByUUIDRequestBodyState, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {WAIT_INSTANCE_BY_UUID_REQUEST_BODY_STATE_VALUES!r}")
