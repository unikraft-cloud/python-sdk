from typing import Literal, cast

CreateInstanceRequestRestartPolicy = Literal["always", "never", "on_failure"]

CREATE_INSTANCE_REQUEST_RESTART_POLICY_VALUES: set[CreateInstanceRequestRestartPolicy] = {
    "always",
    "never",
    "on_failure",
}


def check_create_instance_request_restart_policy(value: str) -> CreateInstanceRequestRestartPolicy:
    if value in CREATE_INSTANCE_REQUEST_RESTART_POLICY_VALUES:
        return cast(CreateInstanceRequestRestartPolicy, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CREATE_INSTANCE_REQUEST_RESTART_POLICY_VALUES!r}")
