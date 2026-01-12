from typing import Literal, cast

InstanceRestartPolicy = Literal["always", "never", "on_failure"]

INSTANCE_RESTART_POLICY_VALUES: set[InstanceRestartPolicy] = {
    "always",
    "never",
    "on_failure",
}


def check_instance_restart_policy(value: str) -> InstanceRestartPolicy:
    if value in INSTANCE_RESTART_POLICY_VALUES:
        return cast(InstanceRestartPolicy, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {INSTANCE_RESTART_POLICY_VALUES!r}")
