from typing import Literal, cast

GetAutoscaleConfigurationsResponseStatus = Literal["error", "success", "unconfigured"]

GET_AUTOSCALE_CONFIGURATIONS_RESPONSE_STATUS_VALUES: set[GetAutoscaleConfigurationsResponseStatus] = {
    "error",
    "success",
    "unconfigured",
}


def check_get_autoscale_configurations_response_status(value: str) -> GetAutoscaleConfigurationsResponseStatus:
    if value in GET_AUTOSCALE_CONFIGURATIONS_RESPONSE_STATUS_VALUES:
        return cast(GetAutoscaleConfigurationsResponseStatus, value)
    raise TypeError(
        f"Unexpected value {value!r}. Expected one of {GET_AUTOSCALE_CONFIGURATIONS_RESPONSE_STATUS_VALUES!r}"
    )
