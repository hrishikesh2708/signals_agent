from __future__ import annotations

from typing import Literal

from app.destinations.registry import get_destination_registry
from app.graph.state import INTENT_MAX_ATTEMPTS, IntentOpenQuestion, IntentPhase, ScopePhase
from app.graph.validators.common import dedupe, get_lookup, resolve_product_groups
from app.internal.signal_type import (
    get_active_signal_type_id,
    get_signal_type,
    get_signal_type_picker_options,
)
from app.sources.registry import get_source_registry

_FIELD_COPY: dict[IntentOpenQuestion, dict[str, str]] = {
    "source": {
        "title": "Select a data source",
        "subtitle": "Choose which CRM or data source to connect.",
    },
    "signal_type": {
        "title": "Confirm the signal type",
        "subtitle": "v1 supports offline conversions — confirm before choosing destinations.",
    },
    "channels": {
        "title": "Select ad destinations",
        "subtitle": "Choose which ad platforms should receive this data.",
    },
}


def scope_hint_ids(scope: ScopePhase | dict | None) -> list[str]:
    """Flatten matched_tokens[].id — compose hints only (clarify-private)."""
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
        "hitl_prompted": False,
    }


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


def _option(
    option_id: str,
    label: str,
    *,
    enabled: bool = True,
    description: str | None = None,
) -> dict:
    return {
        "id": option_id,
        "label": label,
        "enabled": enabled,
        "description": description,
    }


def _options_for_field(open_question: IntentOpenQuestion) -> list[dict]:
    if open_question == "source":
        return [
            _option(source.id, source.display_name, enabled=source.enabled)
            for source in get_source_registry().list_sources()
        ]

    if open_question == "signal_type":
        by_id = {signal.id: signal for signal in get_signal_type().signal_types}
        options: list[dict] = []
        for signal_id, active_flag, reason in get_signal_type_picker_options():
            signal = by_id.get(signal_id)
            label = signal.display_name if signal else signal_id
            options.append(
                _option(signal_id, label, enabled=active_flag, description=reason)
            )
        return options

    if open_question == "channels":
        groups: dict[str, str] = {}
        for destination in get_destination_registry().list_destinations():
            if not destination.product_group:
                continue
            groups.setdefault(destination.product_group, destination.short_label)
        return [
            _option(group_id, label)
            for group_id, label in sorted(groups.items())
        ]

    exhaustive: Literal["source", "signal_type", "channels"] = open_question
    raise ValueError(f"unsupported open_question: {exhaustive}")


def parse_clarify_selection(
    raw: object,
    open_question: IntentOpenQuestion | None,
) -> dict[str, object]:
    """Primary resume contract: ``{ "selected": "<id>" | ["id", ...] }``."""
    if not isinstance(raw, dict) or open_question is None:
        return {}

    selected = raw.get("selected")
    if selected in (None, "", []):
        return {}

    if open_question == "channels":
        if isinstance(selected, list) and selected:
            return {"channels": selected}
        return {}

    if open_question in ("source", "signal_type"):
        if isinstance(selected, str) and selected.strip():
            return {open_question: selected.strip()}
        return {}

    exhaustive: Literal["source", "signal_type", "channels"] = open_question
    raise ValueError(f"unsupported open_question: {exhaustive}")


def merge_intent_selection(
    selection: object,
    current: IntentPhase,
) -> IntentPhase:
    """Thin merge: apply ``selected`` for the current open_question, recompute, clear HITL flag."""
    parsed = parse_clarify_selection(selection, current.get("open_question"))
    lookup = get_lookup()

    source = current["source"]
    signal_type = current["signal_type"]
    channels = list(current["channels"])

    if "source" in parsed:
        source = lookup.normalize_source(str(parsed.get("source"))) or source
    if "signal_type" in parsed:
        signal_type = lookup.normalize_signal_type(str(parsed.get("signal_type"))) or signal_type
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

    return {
        "source": source,
        "channels": channels,
        "destinations": [],
        "signal_type": signal_type,
        "status": "partial",
        "open_question": _next_open_question(source, channels, signal_type),
        "attempt": current["attempt"],
        "hitl_prompted": False,
    }


def build_clarify_payload(intent: IntentPhase) -> dict:
    """Static interrupt value only — not stored on IntentPhase."""
    open_question = intent.get("open_question")
    if open_question is None:
        raise ValueError("build_clarify_payload requires a partial intent with open_question")

    copy = _FIELD_COPY[open_question]
    return {
        "type": "intent_clarify",
        "field": open_question,
        "title": copy["title"],
        "subtitle": copy["subtitle"],
        "required": True,
        "multi": open_question == "channels",
        "options": _options_for_field(open_question),
        "context": {
            "source": intent["source"],
            "signal_type": intent["signal_type"],
            "channels": intent["channels"],
        },
        "attempt": intent["attempt"],
        "max_attempts": INTENT_MAX_ATTEMPTS,
    }
