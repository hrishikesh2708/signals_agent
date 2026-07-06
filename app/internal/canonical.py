# 3. Optimized Load and Query Functions

from functools import lru_cache
from pathlib import Path
import yaml
from app.internal.modal import CanonicalSchemaConfig, CanonicalField
from typing import Tuple

INTERNAL_DIR = Path(__file__).parent
CONFIG_DIR = INTERNAL_DIR / "config"

@lru_cache(maxsize=1)
def load_canonical_config() -> CanonicalSchemaConfig:
    """Reads, validates, and caches the canonical.yaml file."""
    path = CONFIG_DIR / "canonical.yaml"
    with path.open(encoding="utf-8") as handle:
        raw_data = yaml.safe_load(handle)
        
    # Standardize empty/invalid dict root checks
    if not isinstance(raw_data, dict):
        return CanonicalSchemaConfig(destination_type="unknown", version="0.0", fields=[])
        
    return CanonicalSchemaConfig(**raw_data)


def load_canonical_fields() -> Tuple[CanonicalField, ...]:
    """Replaces your legacy _load_canonical_fields() function."""
    config = load_canonical_config()
    return tuple(config.fields)
