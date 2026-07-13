from __future__ import annotations

from app.graph.state import IntentOpenQuestion, IntentPhase, ScopePhase
from app.graph.validators.common import get_lookup, get_mention_parser
from app.internal.signal_type import get_active_signal_type_id
from app.sources.registry import get_source_registry


def scope_hint_ids(scope: ScopePhase | dict | None) -> list[str]:
    """Flatten matched_tokens[].id from global scope state (capture-private)."""
    if not scope:
        return []
    tokens = scope.get("matched_tokens") or []
    ids: list[str] = []
    for token in tokens:
        if not isinstance(token, dict):
            continue
        token_id = token.get("id")
        if isinstance(token_id, str) and token_id and token_id not in ids:
            ids.append(token_id)
    return ids


def _infer_signal_type(text: str, scope_tokens: list[str]) -> str | None:
    active = get_active_signal_type_id()
    if active in scope_tokens:
        return active
    if get_mention_parser().offline_signal_in_text(text):
        return active
    return None


def _next_open_question(
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


def _normalize_channels(raw_channels: list[str]) -> list[str]:
    lookup = get_lookup()
    channels: list[str] = []
    for item in raw_channels:
        normalized = lookup.normalize_channel(str(item))
        if normalized and normalized not in channels:
            channels.append(normalized)
    return channels


def build_intent_from_extract(
    raw: dict | None,
    scope_tokens: list[str],
    latest_text: str,
) -> IntentPhase:
    """Build partial intent from capture LLM JSON — source / signal_type / channels only."""
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

    for token in scope_tokens:
        if token in source_registry.source_ids and source is None:
            source = token
        if token == active and signal_type is None:
            signal_type = token
        if token in product_groups and token not in channels:
            channels.append(token)

    if signal_type != active:
        inferred = _infer_signal_type(latest_text, scope_tokens)
        if inferred:
            signal_type = inferred

    if signal_type != active:
        signal_type = None

    return {
        "source": source,
        "channels": channels,
        "destinations": [],
        "signal_type": signal_type,
        "status": "partial",
        "open_question": _next_open_question(source, channels, signal_type),
        "attempt": 1,
    }
