from typing import Literal, cast

WaitInstanceResponseWaitedInstanceState = Literal["draining", "running", "standby", "starting", "stopped", "stopping"]

WAIT_INSTANCE_RESPONSE_WAITED_INSTANCE_STATE_VALUES: set[WaitInstanceResponseWaitedInstanceState] = {
    "draining",
    "running",
    "standby",
    "starting",
    "stopped",
    "stopping",
}


def check_wait_instance_response_waited_instance_state(value: str) -> WaitInstanceResponseWaitedInstanceState:
    if value in WAIT_INSTANCE_RESPONSE_WAITED_INSTANCE_STATE_VALUES:
        return cast(WaitInstanceResponseWaitedInstanceState, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {WAIT_INSTANCE_RESPONSE_WAITED_INSTANCE_STATE_VALUES!r}"
    )
