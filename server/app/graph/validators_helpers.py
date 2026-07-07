from __future__ import annotations

import re
from functools import lru_cache

from app.destinations.registry import (
    GOOGLE_CUSTOMER_MATCH,
    VALID_PLATFORMS,
    DestinationRegistry,
    get_destination_registry,
)
from app.internal.signal_type import get_active_signal_type_id, load_signal_types_config
from app.sources.registry import SourceRegistry, get_source_registry


class Lookup:
    def __init__(
        self,
        source_registry: SourceRegistry,
        destination_registry: DestinationRegistry,
    ) -> None:
        self._source_registry = source_registry
        self._destination_registry = destination_registry
        self._index = self._build_index(source_registry, destination_registry)

    @staticmethod
    def _build_index(
        source_registry: SourceRegistry,
        destination_registry: DestinationRegistry,
    ) -> dict[str, str]:
        index: dict[str, str] = {}
        for source in source_registry.list_sources():
            index[source.id.lower()] = source.id
            index[source.display_name.lower()] = source.id
            for alias in source.aliases:
                index[alias.lower()] = source.id

        for destination in destination_registry.list_destinations():
            index[destination.id.lower()] = destination.id
            index[destination.channel_display_name.lower()] = destination.id
            index[destination.display_name.lower()] = destination.id
            for alias in destination.aliases:
                index[alias.lower()] = destination.id

        for signal in load_signal_types_config().signal_types:
            index[signal.id.lower()] = signal.id
            for alias in signal.aliases:
                index[alias.lower()] = signal.id

        return index

    def resolve(self, token: str) -> str | None:
        return self._index.get(token.strip().lower())

    def normalize_tokens(self, tokens: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for token in tokens:
            canonical = self.resolve(token)
            if canonical and canonical not in seen:
                seen.add(canonical)
                normalized.append(canonical)
        return normalized

    def normalize_source(self, value: str | None) -> str | None:
        if not value:
            return None
        canonical = self.resolve(value)
        if canonical in self._source_registry.source_ids:
            return canonical
        return None

    def normalize_signal_type(self, value: str | None) -> str | None:
        if not value:
            return None
        canonical = self.resolve(value)
        active = get_active_signal_type_id()
        if canonical == active:
            return active
        return None

    def normalize_connector(self, value: str) -> str | None:
        canonical = self.resolve(value)
        if canonical in self._destination_registry.destination_ids:
            return canonical
        return None


@lru_cache
def get_lookup() -> Lookup:
    return Lookup(get_source_registry(), get_destination_registry())


class MentionParser:
    def __init__(self, destination_registry: DestinationRegistry) -> None:
        self._destination_registry = destination_registry
        self._platform_patterns = self._build_platform_patterns(destination_registry)
        self._connector_patterns = self._build_connector_patterns(destination_registry)

    @staticmethod
    def _build_platform_patterns(
        destination_registry: DestinationRegistry,
    ) -> list[tuple[str, re.Pattern[str]]]:
        terms_by_platform: dict[str, set[str]] = {}
        for entry in destination_registry.list_destinations():
            platform = entry.platform
            if not platform:
                continue
            terms = terms_by_platform.setdefault(platform, set())
            terms.add(platform)
            terms.update(entry.aliases)

        patterns: list[tuple[str, re.Pattern[str]]] = []
        for platform, terms in terms_by_platform.items():
            for term in terms:
                escaped = re.escape(term.lower())
                patterns.append((platform, re.compile(rf"\b{escaped}\b", re.IGNORECASE)))
        return patterns

    @staticmethod
    def _build_connector_patterns(
        destination_registry: DestinationRegistry,
    ) -> list[tuple[str, re.Pattern[str]]]:
        patterns: list[tuple[str, re.Pattern[str]]] = []
        for entry in destination_registry.list_destinations():
            terms = {entry.id, entry.display_name, entry.channel_display_name, *entry.aliases}
            for term in terms:
                escaped = re.escape(term.lower())
                patterns.append((entry.id, re.compile(rf"\b{escaped}\b", re.IGNORECASE)))
        return patterns

    def platforms_in_text(self, text: str) -> list[str]:
        hits: list[str] = []
        for platform, pattern in self._platform_patterns:
            if pattern.search(text) and platform not in hits:
                hits.append(platform)
        return hits

    def connectors_in_text(self, text: str) -> list[str]:
        hits: list[str] = []
        for dest_id, pattern in self._connector_patterns:
            if pattern.search(text) and dest_id not in hits:
                hits.append(dest_id)
        return hits

    def offline_signal_in_text(self, text: str) -> bool:
        active = get_active_signal_type_id()
        text_lower = text.lower()
        for signal in load_signal_types_config().signal_types:
            if signal.id != active:
                continue
            for alias in signal.aliases:
                if re.search(rf"\b{re.escape(alias.lower())}\b", text_lower):
                    return True
        return False


@lru_cache
def get_mention_parser() -> MentionParser:
    return MentionParser(get_destination_registry())


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def connector_to_platform(dest_id: str) -> str | None:
    entry = get_destination_registry().get_destination(dest_id)
    if entry is None:
        return None
    return entry.platform


def sanitize_platform(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in VALID_PLATFORMS:
        return normalized
    return None


def resolve_product_groups(
    destination_registry: DestinationRegistry,
    named: list[str],
    text: str,
    signal_type: str | None,
) -> list[str]:
    by_id = destination_registry.destinations_by_id()
    groups: dict[str, list[str]] = {}
    ungrouped: list[str] = []

    for dest_id in dedupe(named):
        entry = by_id.get(dest_id)
        if entry is None:
            continue
        if entry.product_group:
            groups.setdefault(entry.product_group, []).append(dest_id)
        else:
            ungrouped.append(dest_id)

    text_lower = text.lower()
    resolved = list(ungrouped)

    for members in groups.values():
        if len(members) == 1:
            resolved.append(members[0])
            continue

        picked: list[str] = []
        for member in members:
            member_entry = by_id[member]
            for phrase in member_entry.disambiguators:
                if phrase.lower() in text_lower:
                    picked = [member]
                    break
            if picked:
                break

        if not picked and signal_type:
            for member in members:
                if signal_type in by_id[member].signal_types:
                    picked = [member]
                    break

        if not picked:
            defaults = [member for member in members if by_id[member].group_default]
            picked = defaults or [members[0]]

        resolved.append(picked[0])

    return dedupe(resolved)


def apply_v1_channel_rules(
    destination_registry: DestinationRegistry,
    channels: list[str],
    text: str,
    signal_type: str | None,
) -> list[str]:
    if GOOGLE_CUSTOMER_MATCH in channels:
        channels = [channel for channel in channels if channel != GOOGLE_CUSTOMER_MATCH]
    return resolve_product_groups(destination_registry, channels, text, signal_type)


def resolve_platforms_to_channels(
    destination_registry: DestinationRegistry,
    platforms: list[str],
    text: str,
    signal_type: str,
) -> list[str]:
    by_id = destination_registry.destinations_by_id()
    channels: list[str] = []

    for platform in dedupe(platforms):
        members = [entry.id for entry in by_id.values() if entry.platform == platform]
        if not members:
            continue
        if len(members) == 1:
            channels.append(members[0])
            continue
        channels.extend(resolve_product_groups(destination_registry, members, text, signal_type))

    return apply_v1_channel_rules(destination_registry, dedupe(channels), text, signal_type)


def mention_destinations(text: str, signal_type: str | None = None) -> list[str]:
    destination_registry = get_destination_registry()
    hits = get_mention_parser().connectors_in_text(text)
    return resolve_product_groups(destination_registry, hits, text, signal_type)
