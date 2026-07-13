from __future__ import annotations

from typing import Literal

from app.destinations.registry import get_destination_registry
from app.graph.state import INTENT_MAX_ATTEMPTS, IntentOpenQuestion, IntentPhase
from app.graph.validators.common import (
    dedupe,
    get_lookup,
    resolve_product_groups,
    sanitize_platform,
)
from app.graph.validators.intent_capture import normalize_intent
from app.internal.signal_type import (
    get_active_signal_type_id,
    get_signal_type_picker_options,
)
from app.sources.registry import get_source_registry


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
        "missing": [],
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
        return normalize_intent(
            current["source"],
            list(current.get("platform_mentions", [])),
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
    platform_mentions = list(current.get("platform_mentions", []))

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

    return normalize_intent(
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
            "platform_mentions": intent.get("platform_mentions", []),
            "options": [
                {"id": signal_id, "active": active_flag, "reason": reason}
                for signal_id, active_flag, reason in get_signal_type_picker_options()
            ],
        }
    elif open_question == "channels":
        suggested = list(intent["channels"]) or list(intent.get("platform_mentions", []))
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
            "platform_mentions": intent.get("platform_mentions", []),
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
            "platform_mentions": intent.get("platform_mentions", []),
            "channels": intent["channels"],
            "signal_type": intent["signal_type"],
        },
        "field": field,
    }
