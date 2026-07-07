from __future__ import annotations

_CONNECTOR_CLASSES: dict[str, type] = {}


def register_destination(destination_id: str):
    def decorator(cls: type) -> type:
        _CONNECTOR_CLASSES[destination_id] = cls
        return cls

    return decorator


def registered_connector_classes() -> dict[str, type]:
    return dict(_CONNECTOR_CLASSES)
