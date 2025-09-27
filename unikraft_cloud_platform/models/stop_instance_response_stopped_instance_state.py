from typing import Literal, cast

StopInstanceResponseStoppedInstanceState = Literal["draining", "running", "standby", "starting", "stopped", "stopping"]

STOP_INSTANCE_RESPONSE_STOPPED_INSTANCE_STATE_VALUES: set[StopInstanceResponseStoppedInstanceState] = {
    "draining",
    "running",
    "standby",
    "starting",
    "stopped",
    "stopping",
}


def check_stop_instance_response_stopped_instance_state(value: str) -> StopInstanceResponseStoppedInstanceState:
    if value in STOP_INSTANCE_RESPONSE_STOPPED_INSTANCE_STATE_VALUES:
        return cast(StopInstanceResponseStoppedInstanceState, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {STOP_INSTANCE_RESPONSE_STOPPED_INSTANCE_STATE_VALUES!r}"
    )
