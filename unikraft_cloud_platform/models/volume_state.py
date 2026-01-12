from typing import Literal, cast

VolumeState = Literal["available", "busy", "error", "idle", "initializing", "mounted", "uninitialized"]

VOLUME_STATE_VALUES: set[VolumeState] = {
    "available",
    "busy",
    "error",
    "idle",
    "initializing",
    "mounted",
    "uninitialized",
}


def check_volume_state(value: str) -> VolumeState:
    if value in VOLUME_STATE_VALUES:
        return cast(VolumeState, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {VOLUME_STATE_VALUES!r}")
