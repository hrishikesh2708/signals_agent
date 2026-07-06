from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.destinations.exceptions import DestinationConfigError
from app.destinations.spec import Destination

CONFIG_DIR = Path(__file__).parent / "config"

_CATALOG_FIELD_MAP = {
    "enabled": "enabled",
    "label": "display_name",
    "short_label": "short_label",
    "detail": "detail",
    "aliases": "aliases",
    "product_group": "product_group",
    "group_default": "group_default",
    "disambiguators": "disambiguators",
    "signal_types": "signal_types",
    "event_destination": "event_destination",
    "match_keys": "match_keys",
    "required_metadata": "required_metadata",
    "per_stage": "per_stage",
}


def _normalize_raw(raw: dict) -> dict:
    """Map legacy YAML nesting to flat Destination fields before validation."""
    out = dict(raw)

    if "destination_type" in raw and "id" not in raw:
        out["id"] = raw["destination_type"]

    catalog = raw.get("catalog")
    if isinstance(catalog, dict):
        for catalog_key, model_key in _CATALOG_FIELD_MAP.items():
            if catalog_key in catalog and model_key not in out:
                out[model_key] = catalog[catalog_key]
        if "oauth_path" in catalog and "oauth" not in out:
            out["oauth"] = {"start_path": catalog["oauth_path"]}

    if "oauth_path" in raw and "oauth" not in out:
        out["oauth"] = {"start_path": raw["oauth_path"]}

    return out


def load_destination(path: Path) -> Destination:
    if not path.is_file():
        raise DestinationConfigError(f"{path}: file not found")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DestinationConfigError(f"{path}: invalid YAML — {exc}") from exc

    if not isinstance(raw, dict):
        raise DestinationConfigError(f"{path}: top-level content must be a mapping")

    try:
        destination = Destination.model_validate(_normalize_raw(raw))
    except ValidationError as exc:
        raise DestinationConfigError(f"{path}: {exc}") from exc

    expected_name = f"{destination.id}.yaml"
    if path.name != expected_name:
        raise DestinationConfigError(
            f"{path}: file name must be {expected_name!r} to match id={destination.id!r}"
        )

    return destination


def load_all_destinations() -> dict[str, Destination]:
    destinations: dict[str, Destination] = {}
    paths = sorted(CONFIG_DIR.glob("*.yaml"))

    if not paths:
        raise DestinationConfigError(f"No destination configs found in {CONFIG_DIR}")

    errors: list[str] = []
    for path in paths:
        try:
            destination = load_destination(path)
        except DestinationConfigError as exc:
            errors.append(str(exc))
            continue
        if destination.id in destinations:
            errors.append(
                f"{path}: duplicate destination id {destination.id!r} "
                "(already loaded from another file)"
            )
            continue
        destinations[destination.id] = destination

    if errors:
        raise DestinationConfigError(
            "Failed to load destination configs:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return destinations
