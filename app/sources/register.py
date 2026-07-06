from __future__ import annotations

_CONNECTOR_CLASSES: dict[str, type] = {}


def register_source(source_id: str):
    def decorator(cls: type) -> type:
        _CONNECTOR_CLASSES[source_id] = cls
        return cls

    return decorator


def registered_connector_classes() -> dict[str, type]:
    return dict(_CONNECTOR_CLASSES)
