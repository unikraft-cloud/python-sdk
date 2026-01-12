from typing import Literal, cast

WaitInstancesState = Literal["draining", "running", "standby", "starting", "stopped", "stopping"]

WAIT_INSTANCES_STATE_VALUES: set[WaitInstancesState] = {
    "draining",
    "running",
    "standby",
    "starting",
    "stopped",
    "stopping",
}


def check_wait_instances_state(value: str) -> WaitInstancesState:
    if value in WAIT_INSTANCES_STATE_VALUES:
        return cast(WaitInstancesState, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {WAIT_INSTANCES_STATE_VALUES!r}")
