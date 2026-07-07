from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from app.sources.exceptions import SourceConfigError, SourceRegistryError
from app.sources.loader import load_all_sources
from app.sources.protocol import SourceConnector, SourceField
from app.sources.register import registered_connector_classes
from app.sources.spec import Source


def env_value(name: str, *, default: str | None = None) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if default is not None:
        return default
    raise SourceRegistryError(f"Missing required environment variable: {name}")


@dataclass(frozen=True)
class SourceRegistry:
    sources: tuple[Source, ...]
    _connectors: dict[str, SourceConnector]

    @property
    def source_ids(self) -> frozenset[str]:
        return frozenset(source.id for source in self.sources)

    def get_source(self, source_id: str) -> Source | None:
        for source in self.sources:
            if source.id == source_id:
                return source
        return None

    def get_connector(self, source_id: str) -> SourceConnector:
        connector = self._connectors.get(source_id)
        if connector is None:
            raise KeyError(f"No connector registered for source {source_id!r}")
        return connector

    def list_sources(self, *, enabled_only: bool = True) -> list[Source]:
        if enabled_only:
            return [source for source in self.sources if source.enabled]
        return list(self.sources)

    def resolve_source(self, text: str) -> str | None:
        needle = text.strip().lower()
        if not needle:
            return None
        for source in self.sources:
            if not source.enabled:
                continue
            candidates = {
                source.id.lower(),
                source.display_name.lower(),
                *(alias.lower() for alias in source.aliases),
            }
            if needle in candidates:
                return source.id
        return None

    def is_supported_source(self, source_id: str) -> bool:
        source = self.get_source(source_id)
        return source is not None and source.enabled

    async def describe_object(
        self,
        source_id: str,
        instance_url: str,
        access_token: str,
        object_name: str,
    ) -> list[SourceField]:
        connector = self.get_connector(source_id)
        return await connector.describe_object(instance_url, access_token, object_name)


def _build_registry() -> SourceRegistry:
    connector_classes = registered_connector_classes()
    all_sources = load_all_sources()
    enabled_sources = [source for source in all_sources.values() if source.enabled]

    for source in enabled_sources:
        if connector_classes.get(source.id) is None:
            raise SourceRegistryError(
                f"Enabled source {source.id!r} has config but no connector class registered"
            )

    enabled_ids = {source.id for source in enabled_sources}
    orphan_connectors = set(connector_classes) - enabled_ids
    if orphan_connectors:
        raise SourceRegistryError(
            f"Connector(s) registered without enabled source config: {sorted(orphan_connectors)}"
        )

    connectors: dict[str, SourceConnector] = {}
    for source in enabled_sources:
        connector_cls = connector_classes[source.id]
        connector = connector_cls(source)
        if connector.id != source.id:
            raise SourceRegistryError(
                f"Connector id {connector.id!r} does not match source id {source.id!r}"
            )
        connectors[source.id] = connector

    return SourceRegistry(sources=tuple(enabled_sources), _connectors=connectors)


@lru_cache
def get_source_registry() -> SourceRegistry:
    try:
        return _build_registry()
    except SourceConfigError as exc:
        raise SourceRegistryError(str(exc)) from exc


def get_source(source_id: str) -> Source | None:
    return get_source_registry().get_source(source_id)


def get_connector(source_id: str) -> SourceConnector:
    return get_source_registry().get_connector(source_id)


def resolve_source(text: str) -> str | None:
    return get_source_registry().resolve_source(text)


def is_supported_source(source_id: str) -> bool:
    return get_source_registry().is_supported_source(source_id)
