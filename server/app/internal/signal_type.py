from functools import lru_cache
from pathlib import Path

import yaml

from app.internal.modal import SignalTypesConfig

INTERNAL_DIR = Path(__file__).parent
CONFIG_DIR = INTERNAL_DIR / "config"


@lru_cache(maxsize=1)
def load_signal_types_config() -> SignalTypesConfig:
    """Reads, validates, and caches the signal_types.yaml file."""
    path = CONFIG_DIR / "signal_types.yaml"
    with path.open(encoding="utf-8") as handle:
        raw_data = yaml.safe_load(handle)
    return SignalTypesConfig(**raw_data)


def get_signal_type() -> SignalTypesConfig:
    """Public entry point for the full signal-types config."""
    return load_signal_types_config()


def get_signal_type_ids() -> set[str]:
    config = get_signal_type()
    return {signal.id for signal in config.signal_types}


def get_active_signal_type_ids() -> set[str]:
    config = get_signal_type()
    return {signal.id for signal in config.signal_types if signal.active}


def get_active_signal_type_id() -> str:
    config = get_signal_type()
    for signal in config.signal_types:
        if signal.active:
            return signal.id
    raise RuntimeError("No active v1 signal type configured")


def get_signal_type_picker_options() -> list[tuple[str, bool, str | None]]:
    config = get_signal_type()
    options: list[tuple[str, bool, str | None]] = []
    for signal in config.signal_types:
        if signal.active:
            options.append((signal.id, True, None))
        else:
            options.append((signal.id, False, "Not available"))
    return options
