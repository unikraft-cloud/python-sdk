from typing import Literal, cast

InstanceState = Literal["draining", "running", "standby", "starting", "stopped", "stopping"]

INSTANCE_STATE_VALUES: set[InstanceState] = {
    "draining",
    "running",
    "standby",
    "starting",
    "stopped",
    "stopping",
}


def check_instance_state(value: str) -> InstanceState:
    if value in INSTANCE_STATE_VALUES:
        return cast(InstanceState, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {INSTANCE_STATE_VALUES!r}")
