from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.destinations.exceptions import DestinationConfigError, DestinationRegistryError
from app.destinations.loader import load_all_destinations
from app.destinations.spec import Destination

GOOGLE_OFFLINE_CONVERSIONS = "google_offline_conversions"
GOOGLE_CUSTOMER_MATCH = "google_customer_match"
VALID_PLATFORMS = frozenset({"google", "meta"})


@dataclass(frozen=True)
class DestinationRegistry:
    destinations: tuple[Destination, ...]

    @property
    def destination_ids(self) -> frozenset[str]:
        return frozenset(destination.id for destination in self.destinations)

    def get_destination(self, dest_id: str) -> Destination | None:
        for destination in self.destinations:
            if destination.id == dest_id:
                return destination
        return None

    def destinations_by_id(self) -> dict[str, Destination]:
        return {entry.id: entry for entry in self.destinations}

    def list_destinations(self, *, enabled_only: bool = True) -> list[Destination]:
        if enabled_only:
            return [destination for destination in self.destinations if destination.enabled]
        return list(self.destinations)

    def resolve_destination(self, text: str) -> str | None:
        needle = text.strip().lower()
        if not needle:
            return None
        for destination in self.destinations:
            if not destination.enabled:
                continue
            candidates = {
                destination.id.lower(),
                destination.display_name.lower(),
                destination.short_label.lower(),
                *(alias.lower() for alias in destination.aliases),
            }
            if needle in candidates:
                return destination.id
        return None

    def is_supported_destination(self, dest_id: str) -> bool:
        destination = self.get_destination(dest_id)
        return destination is not None and destination.enabled

    def is_v1_active(self, dest_id: str) -> tuple[bool, str | None]:
        entry = self.get_destination(dest_id)
        if entry is not None and "audience" in entry.signal_types:
            return False, "Audience / Customer Match not in v1 (offline only)"
        return True, None

    def routing_meta(self) -> dict[str, dict[str, Any]]:
        meta: dict[str, dict[str, Any]] = {}
        for entry in self.destinations:
            meta[entry.id] = {
                "product_group": entry.product_group,
                "group_default": entry.group_default,
                "disambiguators": list(entry.disambiguators),
                "signal_types": list(entry.signal_types),
                "oauth_path": entry.oauth_path,
                "event_destination": entry.event_destination,
                "match_keys": list(entry.match_keys),
                "required_metadata": [
                    item.model_dump() for item in entry.required_metadata
                ],
                "per_stage": {
                    key: value.model_dump() for key, value in entry.per_stage.items()
                },
            }
        return meta

    def catalog_api_entry(self, dest_id: str) -> dict[str, Any] | None:
        entry = self.get_destination(dest_id)
        if entry is None:
            return None

        per_stage_input: str | None = None
        event_name_stage = entry.per_stage.get("event_name")
        if event_name_stage is not None and event_name_stage.fill == "user":
            per_stage_input = event_name_stage.field

        return {
            "id": entry.id,
            "label": entry.display_name,
            "shortLabel": entry.short_label,
            "oauthPath": entry.oauth_path,
            "eventDestination": entry.event_destination,
            "requiredMetadata": [
                {
                    "key": item.key,
                    "label": item.label,
                    "secret": item.secret,
                }
                for item in entry.required_metadata
            ],
            "perStageInput": per_stage_input,
        }


def _build_registry() -> DestinationRegistry:
    all_destinations = load_all_destinations()
    enabled = [destination for destination in all_destinations.values() if destination.enabled]
    return DestinationRegistry(destinations=tuple(enabled))


@lru_cache
def get_destination_registry() -> DestinationRegistry:
    try:
        return _build_registry()
    except DestinationConfigError as exc:
        raise DestinationRegistryError(str(exc)) from exc


def get_destination(dest_id: str) -> Destination | None:
    return get_destination_registry().get_destination(dest_id)


def list_destinations() -> list[Destination]:
    return get_destination_registry().list_destinations()


def resolve_destination(text: str) -> str | None:
    return get_destination_registry().resolve_destination(text)


def is_supported_destination(dest_id: str) -> bool:
    return get_destination_registry().is_supported_destination(dest_id)


def get_destination_ids() -> frozenset[str]:
    return get_destination_registry().destination_ids


def get_routing_meta() -> dict[str, dict[str, Any]]:
    return get_destination_registry().routing_meta()


def is_v1_active(dest_id: str) -> tuple[bool, str | None]:
    return get_destination_registry().is_v1_active(dest_id)


def catalog_api_entry(dest_id: str) -> dict[str, Any] | None:
    return get_destination_registry().catalog_api_entry(dest_id)
