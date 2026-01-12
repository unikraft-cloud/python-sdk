from typing import Literal, cast

GetInstanceLogsResponseLoggedInstanceState = Literal[
    "draining", "running", "standby", "starting", "stopped", "stopping"
]

GET_INSTANCE_LOGS_RESPONSE_LOGGED_INSTANCE_STATE_VALUES: set[GetInstanceLogsResponseLoggedInstanceState] = {
    "draining",
    "running",
    "standby",
    "starting",
    "stopped",
    "stopping",
}


def check_get_instance_logs_response_logged_instance_state(value: str) -> GetInstanceLogsResponseLoggedInstanceState:
    if value in GET_INSTANCE_LOGS_RESPONSE_LOGGED_INSTANCE_STATE_VALUES:
        return cast(GetInstanceLogsResponseLoggedInstanceState, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {GET_INSTANCE_LOGS_RESPONSE_LOGGED_INSTANCE_STATE_VALUES!r}"
    )
