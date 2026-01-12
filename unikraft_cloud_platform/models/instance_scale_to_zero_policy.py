from typing import Literal, cast

InstanceScaleToZeroPolicy = Literal["idle", "off", "on"]

INSTANCE_SCALE_TO_ZERO_POLICY_VALUES: set[InstanceScaleToZeroPolicy] = {
    "idle",
    "off",
    "on",
}


def check_instance_scale_to_zero_policy(value: str) -> InstanceScaleToZeroPolicy:
    if value in INSTANCE_SCALE_TO_ZERO_POLICY_VALUES:
        return cast(InstanceScaleToZeroPolicy, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {INSTANCE_SCALE_TO_ZERO_POLICY_VALUES!r}")
