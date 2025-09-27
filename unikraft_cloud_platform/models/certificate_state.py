from typing import Literal, cast

CertificateState = Literal["error", "pending", "valid"]

CERTIFICATE_STATE_VALUES: set[CertificateState] = {
    "error",
    "pending",
    "valid",
}


def check_certificate_state(value: str) -> CertificateState:
    if value in CERTIFICATE_STATE_VALUES:
        return cast(CertificateState, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CERTIFICATE_STATE_VALUES!r}")
