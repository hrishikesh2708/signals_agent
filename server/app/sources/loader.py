from pathlib import Path

import yaml
from pydantic import ValidationError

from app.sources.exceptions import SourceConfigError
from app.sources.spec import Source

CONFIG_DIR = Path(__file__).parent / "config"


def _normalize_raw(raw: dict) -> dict:
    """Map YAML nesting to flat Source fields before validation."""
    out = dict(raw)
    objects = raw.get("objects")
    if isinstance(objects, dict):
        if "common" in objects:
            out["objects_common"] = objects["common"]
        if "discover" in objects:
            out["objects_discover"] = objects["discover"]
    return out


def load_source(path: Path) -> Source:
    if not path.is_file():
        raise SourceConfigError(f"{path}: file not found")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise SourceConfigError(f"{path}: invalid YAML — {e}") from e

    if not isinstance(raw, dict):
        raise SourceConfigError(f"{path}: top-level content must be a mapping")

    try:
        source = Source.model_validate(_normalize_raw(raw))
    except ValidationError as e:
        raise SourceConfigError(f"{path}: {e}") from e

    expected_name = f"{source.id}.yaml"
    if path.name != expected_name:
        raise SourceConfigError(
            f"{path}: file name must be {expected_name!r} to match id={source.id!r}"
        )

    return source


def load_all_sources() -> dict[str, Source]:
    sources: dict[str, Source] = {}
    paths = sorted(CONFIG_DIR.glob("*.yaml"))

    if not paths:
        raise SourceConfigError(f"No source configs found in {CONFIG_DIR}")

    errors: list[str] = []
    for path in paths:
        try:
            source = load_source(path)
        except SourceConfigError as e:
            errors.append(str(e))
            continue
        if source.id in sources:
            errors.append(
                f"{path}: duplicate source id {source.id!r} (already loaded from another file)"
            )
            continue
        sources[source.id] = source

    if errors:
        raise SourceConfigError(
            "Failed to load source configs:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return sources
