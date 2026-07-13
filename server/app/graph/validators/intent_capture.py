from __future__ import annotations

from app.graph.state import IntentOpenQuestion, IntentPhase
from app.graph.validators.common import (
    dedupe,
    get_lookup,
    get_mention_parser,
    sanitize_platform,
)
from app.internal.signal_type import get_active_signal_type_id
from app.sources.registry import get_source_registry


def infer_signal_type(text: str, scope_tokens: list[str]) -> str | None:
    active = get_active_signal_type_id()
    if active in scope_tokens:
        return active
    if get_mention_parser().offline_signal_in_text(text):
        return active
    return None


def next_open_question(
    source: str | None,
    channels: list[str],
    signal_type: str | None,
) -> IntentOpenQuestion | None:
    active = get_active_signal_type_id()
    if not source:
        return "source"
    if signal_type != active:
        return "signal_type"
    if not channels:
        return "channels"
    return None


def _collect_platform_mentions(
    platform_mentions: list[str],
    scope_platforms: list[str],
    text: str,
    channels: list[str],
) -> list[str]:
    """Keep platform_mentions in sync with product_group channels (clarify bridge)."""
    merged = list(platform_mentions)
    for item in scope_platforms:
        if item not in merged:
            merged.append(item)
    for item in get_mention_parser().platforms_in_text(text):
        if item not in merged:
            merged.append(item)
    for channel in channels:
        if channel not in merged:
            merged.append(channel)
    return dedupe(merged)


def _normalize_channels(raw_channels: list[str]) -> list[str]:
    lookup = get_lookup()
    channels: list[str] = []
    for item in raw_channels:
        normalized = lookup.normalize_channel(str(item))
        if normalized and normalized not in channels:
            channels.append(normalized)
    return channels


def normalize_intent(
    source: str | None,
    platform_mentions: list[str],
    channels: list[str],
    signal_type: str | None,
    attempt: int,
    text: str,
    scope_tokens: list[str] | None = None,
    scope_platforms: list[str] | None = None,
) -> IntentPhase:
    """Normalize human intent fields. Never derives destinations (clarify owns that)."""
    active = get_active_signal_type_id()
    scope_tokens = scope_tokens or []
    scope_platforms = scope_platforms or []

    channels = _normalize_channels(list(channels))
    platform_mentions = _collect_platform_mentions(
        platform_mentions,
        scope_platforms,
        text,
        channels,
    )
    # Prefer explicit channels; fall back to platform mentions as product_groups.
    if not channels and platform_mentions:
        channels = _normalize_channels(platform_mentions)

    if signal_type != active:
        inferred = infer_signal_type(text, scope_tokens)
        if inferred:
            signal_type = inferred

    if signal_type != active:
        signal_type = None

    open_question = next_open_question(source, channels, signal_type)
    missing: list[str] = []
    if not source:
        missing.append("source")
    if signal_type != active:
        missing.append("signal_type")
    if not channels:
        missing.append("channels")

    # status=complete only after destinations are derived in clarify.
    return {
        "source": source,
        "platform_mentions": platform_mentions,
        "channels": channels,
        "destinations": [],
        "signal_type": signal_type,
        "status": "partial",
        "open_question": open_question,
        "attempt": attempt,
        "missing": missing,
    }


def recompute_intent(
    source: str | None,
    platform_mentions: list[str],
    channels: list[str],
    signal_type: str | None,
    attempt: int,
) -> IntentPhase:
    return normalize_intent(
        source,
        platform_mentions,
        channels,
        signal_type,
        attempt,
        text="",
        scope_tokens=[],
        scope_platforms=[],
    )


def build_intent_from_extract(
    raw: dict | None,
    scope_tokens: list[str],
    latest_text: str,
    scope_platforms: list[str] | None = None,
) -> IntentPhase:
    """Build intent from capture LLM JSON — source / signal_type / channels only."""
    lookup = get_lookup()
    source_registry = get_source_registry()
    active = get_active_signal_type_id()
    product_groups = lookup.product_group_ids()

    source = lookup.normalize_source(raw.get("source") if raw else None)
    signal_type = lookup.normalize_signal_type(raw.get("signal_type") if raw else None)

    channels: list[str] = []
    raw_channels = raw.get("channels") if raw else None
    if isinstance(raw_channels, list):
        channels = _normalize_channels([str(item) for item in raw_channels])

    platform_mentions: list[str] = []
    raw_platforms = raw.get("platform_mentions") if raw else None
    if isinstance(raw_platforms, list):
        for item in raw_platforms:
            platform = sanitize_platform(str(item))
            if platform and platform not in platform_mentions:
                platform_mentions.append(platform)

    for token in scope_tokens:
        if token in source_registry.source_ids and source is None:
            source = token
        if token == active and signal_type is None:
            signal_type = token
        if token in product_groups and token not in channels:
            channels.append(token)

    return normalize_intent(
        source,
        platform_mentions,
        channels,
        signal_type,
        attempt=1,
        text=latest_text,
        scope_tokens=scope_tokens,
        scope_platforms=scope_platforms,
    )
