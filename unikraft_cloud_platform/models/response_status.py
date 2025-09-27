from typing import Literal, cast

ResponseStatus = Literal["error", "success"]

RESPONSE_STATUS_VALUES: set[ResponseStatus] = {
    "error",
    "success",
}


def check_response_status(value: str) -> ResponseStatus:
    if value in RESPONSE_STATUS_VALUES:
        return cast(ResponseStatus, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {RESPONSE_STATUS_VALUES!r}")
