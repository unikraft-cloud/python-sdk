from typing import Literal, cast

StopInstanceResponseStoppedInstancePreviousState = Literal[
    "draining", "running", "standby", "starting", "stopped", "stopping"
]

STOP_INSTANCE_RESPONSE_STOPPED_INSTANCE_PREVIOUS_STATE_VALUES: set[StopInstanceResponseStoppedInstancePreviousState] = {
    "draining",
    "running",
    "standby",
    "starting",
    "stopped",
    "stopping",
}


def check_stop_instance_response_stopped_instance_previous_state(
    value: str,
) -> StopInstanceResponseStoppedInstancePreviousState:
    if value in STOP_INSTANCE_RESPONSE_STOPPED_INSTANCE_PREVIOUS_STATE_VALUES:
        return cast(StopInstanceResponseStoppedInstancePreviousState, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {STOP_INSTANCE_RESPONSE_STOPPED_INSTANCE_PREVIOUS_STATE_VALUES!r}"
    )
