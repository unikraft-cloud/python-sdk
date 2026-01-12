from typing import Literal, cast

ServiceHandlersItem = Literal["http", "redirect", "tls"]

SERVICE_HANDLERS_ITEM_VALUES: set[ServiceHandlersItem] = {
    "http",
    "redirect",
    "tls",
}


def check_service_handlers_item(value: str) -> ServiceHandlersItem:
    if value in SERVICE_HANDLERS_ITEM_VALUES:
        return cast(ServiceHandlersItem, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SERVICE_HANDLERS_ITEM_VALUES!r}")
