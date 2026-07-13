from __future__ import annotations

from typing import Literal

from app.destinations.registry import get_destination_registry
from app.graph.state import INTENT_MAX_ATTEMPTS, IntentOpenQuestion, IntentPhase, ScopePhase
from app.graph.validators.common import (
    dedupe,
    get_lookup,
    get_mention_parser,
    resolve_product_groups,
    sanitize_platform,
)
from app.internal.signal_type import (
    get_active_signal_type_id,
    get_signal_type_picker_options,
)
from app.sources.registry import get_source_registry


def matched_token_ids(scope: ScopePhase | dict | None) -> list[str]:
    """Flatten matched_tokens[].id — clarify-private; barrel re-export keeps node import working."""
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


def derive_destinations(
    channels: list[str],
    signal_type: str | None,
) -> list[str]:
    """Map confirmed product_groups + signal_type → connector ids (Python only)."""
    if not channels or not signal_type:
        return []

    destination_registry = get_destination_registry()
    destinations: list[str] = []

    for group in channels:
        members = [
            entry.id
            for entry in destination_registry.list_destinations()
            if entry.product_group == group and signal_type in entry.signal_types
        ]
        if not members:
            continue
        if len(members) == 1:
            destinations.append(members[0])
            continue
        destinations.extend(resolve_product_groups(destination_registry, members, "", signal_type))

    return dedupe(destinations)


def with_derived_destinations(intent: IntentPhase) -> IntentPhase:
    """Attach machine destinations and mark complete. Call only when human fields are filled."""
    destinations = derive_destinations(intent["channels"], intent["signal_type"])
    return {
        **intent,
        "destinations": destinations,
        "status": "complete",
        "open_question": None,
    }


def _legacy_platform_mentions(intent: IntentPhase) -> list[str]:
    """Phase 2 bridge: IntentPhase no longer stores platform_mentions; reads return []."""
    value = dict(intent).get("platform_mentions", [])
    return list(value) if isinstance(value, list) else []


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


def _collect_platform_mentions(
    platform_mentions: list[str],
    scope_platforms: list[str],
    text: str,
    channels: list[str],
) -> list[str]:
    """Temporary clarify-private bridge until Phase 3 thin merge."""
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


def _normalize_intent(
    source: str | None,
    platform_mentions: list[str],
    channels: list[str],
    signal_type: str | None,
    attempt: int,
    text: str,
    scope_tokens: list[str] | None = None,
    scope_platforms: list[str] | None = None,
) -> IntentPhase:
    """Clarify-private normalize copy (Phase 2 temporary; Phase 3 replaces with thin merge)."""
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
        inferred = _infer_signal_type(text, scope_tokens)
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
        "attempt": attempt,
    }


def parse_clarify_selection(
    raw: object,
    open_question: IntentOpenQuestion | None,
) -> dict[str, object]:
    if raw is None:
        return {}

    if isinstance(raw, str):
        value = raw.strip()
        if not value or open_question is None:
            return {}
        if open_question == "channels":
            return {}
        return {open_question: value}

    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, object] = {}
    for key in ("source", "signal_type", "channels", "platform_mentions"):
        if key in raw and raw[key] is not None:
            normalized[key] = raw[key]
    if normalized:
        return normalized

    field = raw.get("field")
    if not isinstance(field, dict) or open_question is None:
        return {}

    selected = field.get("selected")
    suggested = field.get("suggested")
    value = selected if selected not in (None, "", []) else suggested

    if open_question == "channels":
        if isinstance(value, list) and value:
            return {"channels": value}
        return {}

    if open_question in ("source", "signal_type") and value not in (None, ""):
        return {open_question: value}

    return {}


def merge_intent_selection(
    selection: object,
    current: IntentPhase,
    latest_text: str,
    scope_tokens: list[str] | None = None,
    scope_platforms: list[str] | None = None,
) -> IntentPhase:
    parsed = parse_clarify_selection(selection, current.get("open_question"))
    if not parsed:
        return _normalize_intent(
            current["source"],
            _legacy_platform_mentions(current),
            list(current["channels"]),
            current["signal_type"],
            current["attempt"],
            latest_text,
            scope_tokens,
            scope_platforms,
        )

    lookup = get_lookup()
    source = current["source"]
    signal_type = current["signal_type"]
    channels = list(current["channels"])
    platform_mentions = _legacy_platform_mentions(current)

    if "source" in parsed:
        source = lookup.normalize_source(str(parsed.get("source"))) or source
    if "signal_type" in parsed:
        signal_type = lookup.normalize_signal_type(str(parsed.get("signal_type"))) or signal_type
    if "platform_mentions" in parsed:
        raw_platforms = parsed.get("platform_mentions")
        if isinstance(raw_platforms, list):
            platform_mentions = [
                platform
                for item in raw_platforms
                if (platform := sanitize_platform(str(item))) is not None
            ]
    if "channels" in parsed:
        raw_channels = parsed.get("channels")
        if isinstance(raw_channels, list):
            picked: list[str] = []
            for item in raw_channels:
                normalized = lookup.normalize_channel(str(item))
                if normalized and normalized not in picked:
                    picked.append(normalized)
            if picked:
                channels = picked
                platform_mentions = list(picked)

    return _normalize_intent(
        source,
        platform_mentions,
        channels,
        signal_type,
        current["attempt"],
        latest_text,
        scope_tokens,
        scope_platforms,
    )


def build_clarify_payload(intent: IntentPhase) -> dict:
    destination_registry = get_destination_registry()
    source_registry = get_source_registry()
    open_question = intent.get("open_question")
    if open_question is None:
        raise ValueError("build_clarify_payload requires a partial intent with open_question")

    active = get_active_signal_type_id()

    if open_question == "source":
        field = {
            "suggested": intent["source"],
            "selected": intent["source"],
            "required": True,
            "options": [
                {"id": source.id, "active": True, "reason": None}
                for source in source_registry.list_sources()
            ],
        }
    elif open_question == "signal_type":
        suggested = intent["signal_type"] or active
        field = {
            "suggested": suggested,
            "selected": suggested,
            "required": True,
            "platform_mentions": _legacy_platform_mentions(intent),
            "options": [
                {"id": signal_id, "active": active_flag, "reason": reason}
                for signal_id, active_flag, reason in get_signal_type_picker_options()
            ],
        }
    elif open_question == "channels":
        suggested = list(intent["channels"]) or _legacy_platform_mentions(intent)
        groups: dict[str, str] = {}
        for destination in destination_registry.list_destinations():
            if not destination.product_group:
                continue
            groups.setdefault(destination.product_group, destination.short_label)
        field = {
            "suggested": suggested,
            "selected": intent["channels"] or suggested,
            "required": True,
            "multi": True,
            "platform_mentions": _legacy_platform_mentions(intent),
            "options": [
                {"id": group_id, "active": True, "reason": None, "label": label}
                for group_id, label in sorted(groups.items())
            ],
        }
    else:
        exhaustive: Literal["source", "signal_type", "channels"] = open_question
        raise ValueError(f"unsupported open_question: {exhaustive}")

    return {
        "type": "intent_clarify",
        "open_question": open_question,
        "attempt": intent["attempt"],
        "max_attempts": INTENT_MAX_ATTEMPTS,
        "context": {
            "source": intent["source"],
            "platform_mentions": _legacy_platform_mentions(intent),
            "channels": intent["channels"],
            "signal_type": intent["signal_type"],
        },
        "field": field,
    }
