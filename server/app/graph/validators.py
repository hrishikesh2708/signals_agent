from __future__ import annotations

from typing import Literal, Mapping

from langchain_core.messages import BaseMessage

from app.destinations.registry import get_destination_registry
from app.graph.state import (
    CONFIDENCE_THRESHOLD,
    INTENT_MAX_ATTEMPTS,
    IntentOpenQuestion,
    IntentPhase,
    MatchedToken,
    ScopePhase,
)
from app.graph.validators_helpers import (
    connector_to_platform,
    dedupe,
    get_lookup,
    get_mention_parser,
    resolve_product_groups,
    sanitize_platform,
)
from app.internal.signal_type import (
    get_active_signal_type_id,
    get_active_signal_type_ids,
    get_signal_type,
    get_signal_type_picker_options,
)
from app.sources.registry import get_source_registry

__all__ = [
    "build_clarify_payload",
    "build_intent_from_extract",
    "derive_destinations",
    "infer_signal_type",
    "last_human_text",
    "matched_token_ids",
    "merge_intent_selection",
    "normalize_matched_tokens",
    "parse_clarify_selection",
    "recompute_intent",
    "resolve_product_groups",
    "sanitize_scope_hints",
    "validate_scope_json",
    "with_derived_destinations",
]


def last_human_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if message.type == "human":
            content = message.content
            if isinstance(content, str):
                return content
    return ""


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


def sanitize_scope_hints(
    raw_tokens: list[object],
    text: str = "",
) -> tuple[list[MatchedToken], list[str]]:
    """Validate rich matched_tokens; infer catalog from id; platforms = product_groups."""
    del text  # kept for call-site compatibility; platforms come from product_group ids only
    source_registry = get_source_registry()
    destination_registry = get_destination_registry()
    active_signal_ids = get_active_signal_type_ids()
    signal_by_id = {signal.id: signal for signal in get_signal_type().signal_types}

    product_groups = {
        entry.product_group
        for entry in destination_registry.list_destinations()
        if entry.product_group
    }
    group_labels: dict[str, set[str]] = {}
    for entry in destination_registry.list_destinations():
        if entry.product_group:
            group_labels.setdefault(entry.product_group, set()).add(entry.short_label)

    matched: list[MatchedToken] = []
    seen: set[str] = set()

    for item in raw_tokens:
        if not isinstance(item, dict):
            continue

        raw = item.get("raw")
        token_id = item.get("id")
        if not isinstance(raw, str) or not isinstance(token_id, str):
            continue
        token_id = token_id.strip()
        if not token_id:
            continue

        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        display_name: str | None = None
        canonical_id: str | None = None

        if token_id in source_registry.source_ids:
            source = source_registry.get_source(token_id)
            if source is None:
                continue
            canonical_id = token_id
            display_name = source.display_name
        elif token_id in product_groups:
            canonical_id = token_id
            labels = group_labels.get(canonical_id, set())
            display_name = next(iter(labels)) if len(labels) == 1 else canonical_id.title()
        elif token_id in destination_registry.destination_ids:
            mapped = connector_to_platform(token_id)
            if mapped is None or mapped not in product_groups:
                continue
            canonical_id = mapped
            labels = group_labels.get(canonical_id, set())
            display_name = next(iter(labels)) if len(labels) == 1 else canonical_id.title()
        elif token_id in active_signal_ids:
            signal = signal_by_id.get(token_id)
            if signal is None:
                continue
            canonical_id = token_id
            display_name = signal.display_name
        else:
            continue

        if canonical_id in seen:
            continue
        seen.add(canonical_id)

        matched.append(
            {
                "raw": raw,
                "id": canonical_id,
                "display_name": display_name,
                "confidence": confidence,
            }
        )

    mentioned_platforms = dedupe(
        [token["id"] for token in matched if token["id"] in product_groups]
    )
    return matched, mentioned_platforms


def matched_token_ids(scope: ScopePhase | Mapping[str, object] | None) -> list[str]:
    """Adapter: rich scope tokens → flat id list for intent validators (Step 2 bridge)."""
    if not scope:
        return []
    tokens = scope.get("matched_tokens") or []
    if not isinstance(tokens, list):
        return []
    ids: list[str] = []
    for token in tokens:
        if isinstance(token, dict):
            token_id = token.get("id")
            if isinstance(token_id, str):
                ids.append(token_id)
    return ids


def validate_scope_json(raw: dict | None, latest_text: str = "") -> ScopePhase:
    fallback: ScopePhase = {
        "status": "out_of_scope",
        "reply_kind": "redirect",
        "matched_tokens": [],
        "mentioned_platforms": [],
    }
    if not isinstance(raw, dict):
        return fallback

    status = raw.get("status")
    reply_kind = raw.get("reply_kind")
    raw_tokens = raw.get("matched_tokens")

    if status not in ("in_scope", "out_of_scope"):
        return fallback
    if reply_kind not in ("ack", "greeting", "redirect"):
        return fallback

    if status == "in_scope" and reply_kind != "ack":
        reply_kind = "ack"
    if status == "out_of_scope" and reply_kind == "ack":
        reply_kind = "redirect"

    if not isinstance(raw_tokens, list):
        raw_tokens = []

    matched_tokens, mentioned_platforms = sanitize_scope_hints(raw_tokens, latest_text)

    return {
        "status": status,
        "reply_kind": reply_kind,
        "matched_tokens": matched_tokens,
        "mentioned_platforms": mentioned_platforms,
    }


def normalize_matched_tokens(tokens: list[str]) -> list[str]:
    return get_lookup().normalize_tokens(tokens)


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
