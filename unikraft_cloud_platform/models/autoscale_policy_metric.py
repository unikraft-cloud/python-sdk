from typing import Literal, cast

AutoscalePolicyMetric = Literal["cpu"]

AUTOSCALE_POLICY_METRIC_VALUES: set[AutoscalePolicyMetric] = {
    "cpu",
}


def check_autoscale_policy_metric(value: str) -> AutoscalePolicyMetric:
    if value in AUTOSCALE_POLICY_METRIC_VALUES:
        return cast(AutoscalePolicyMetric, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {AUTOSCALE_POLICY_METRIC_VALUES!r}")
