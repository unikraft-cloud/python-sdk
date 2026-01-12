from typing import Literal, cast

AutoscalePolicyAdjustmentType = Literal["change", "exact", "percentage"]

AUTOSCALE_POLICY_ADJUSTMENT_TYPE_VALUES: set[AutoscalePolicyAdjustmentType] = {
    "change",
    "exact",
    "percentage",
}


def check_autoscale_policy_adjustment_type(value: str) -> AutoscalePolicyAdjustmentType:
    if value in AUTOSCALE_POLICY_ADJUSTMENT_TYPE_VALUES:
        return cast(AutoscalePolicyAdjustmentType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {AUTOSCALE_POLICY_ADJUSTMENT_TYPE_VALUES!r}")
