from __future__ import annotations

from typing import Literal

from langchain_core.messages import BaseMessage

from app.destinations.registry import GOOGLE_CUSTOMER_MATCH, get_destination_registry, is_v1_active
from app.graph.state import INTENT_MAX_ATTEMPTS, IntentOpenQuestion, IntentPhase, ScopePhase
from app.graph.validators_helpers import (
    apply_v1_channel_rules,
    connector_to_platform,
    dedupe,
    get_lookup,
    get_mention_parser,
    mention_destinations,
    resolve_platforms_to_channels,
    resolve_product_groups,
    sanitize_platform,
)
from app.internal.signal_type import get_active_signal_type_id, get_signal_type_picker_options
from app.sources.registry import get_source_registry

__all__ = [
    "build_clarify_payload",
    "build_intent_clarify_payload",
    "build_intent_from_extract",
    "infer_signal_type",
    "last_human_text",
    "merge_intent_selection",
    "mention_destinations",
    "normalize_matched_tokens",
    "parse_clarify_selection",
    "recompute_intent",
    "resolve_product_groups",
    "sanitize_scope_hints",
    "validate_scope_json",
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
    platform_mentions: list[str],
    channels: list[str],
    signal_type: str | None,
) -> IntentOpenQuestion | None:
    active = get_active_signal_type_id()
    if not source:
        return "source"
    if signal_type != active:
        return "signal_type"
    if not channels and not platform_mentions:
        return "channels"
    if not channels:
        return "channels"
    return None


def _collect_platform_mentions(
    platform_mentions: list[str],
    scope_platforms: list[str],
    text: str,
    raw_channels: list[str],
) -> list[str]:
    merged = list(platform_mentions)
    for item in scope_platforms:
        if item not in merged:
            merged.append(item)
    for item in get_mention_parser().platforms_in_text(text):
        if item not in merged:
            merged.append(item)
    for dest_id in raw_channels:
        platform = connector_to_platform(dest_id)
        if platform and platform not in merged:
            merged.append(platform)
    return dedupe(merged)


def _resolve_channels(
    explicit_channels: list[str],
    platform_mentions: list[str],
    text: str,
    signal_type: str,
) -> list[str]:
    destination_registry = get_destination_registry()
    channels = resolve_platforms_to_channels(
        destination_registry, platform_mentions, text, signal_type
    )
    for dest_id in explicit_channels:
        if dest_id not in channels:
            channels.append(dest_id)
    return apply_v1_channel_rules(destination_registry, dedupe(channels), text, signal_type)


def finalize_intent(
    source: str | None,
    platform_mentions: list[str],
    channels: list[str],
    signal_type: str | None,
    attempt: int,
    text: str,
    scope_tokens: list[str] | None = None,
    scope_platforms: list[str] | None = None,
) -> IntentPhase:
    active = get_active_signal_type_id()
    scope_tokens = scope_tokens or []
    scope_platforms = scope_platforms or []
    raw_channels = list(channels)

    platform_mentions = _collect_platform_mentions(
        platform_mentions,
        scope_platforms,
        text,
        raw_channels,
    )

    if signal_type != active:
        inferred = infer_signal_type(text, scope_tokens)
        if inferred:
            signal_type = inferred

    resolved_channels: list[str] = []
    if signal_type == active:
        resolved_channels = _resolve_channels(raw_channels, platform_mentions, text, signal_type)

    open_question = next_open_question(source, platform_mentions, resolved_channels, signal_type)
    missing: list[str] = []
    if not source:
        missing.append("source")
    if signal_type != active:
        missing.append("signal_type")
    if not resolved_channels:
        missing.append("channels")

    status: Literal["complete", "partial"] = "complete" if open_question is None else "partial"
    return {
        "source": source,
        "platform_mentions": platform_mentions,
        "channels": resolved_channels,
        "signal_type": signal_type if signal_type == active else None,
        "status": status,
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
    return finalize_intent(
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
    lookup = get_lookup()
    source_registry = get_source_registry()
    active = get_active_signal_type_id()

    source = lookup.normalize_source(raw.get("source") if raw else None)
    signal_type = lookup.normalize_signal_type(raw.get("signal_type") if raw else None)

    channels: list[str] = []
    raw_channels = raw.get("channels") if raw else None
    if isinstance(raw_channels, list):
        for item in raw_channels:
            normalized = lookup.normalize_connector(str(item))
            if normalized:
                channels.append(normalized)

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

    return finalize_intent(
        source,
        platform_mentions,
        channels,
        signal_type,
        attempt=1,
        text=latest_text,
        scope_tokens=scope_tokens,
        scope_platforms=scope_platforms,
    )


def sanitize_scope_hints(tokens: list[str], text: str) -> tuple[list[str], list[str]]:
    source_registry = get_source_registry()
    destination_registry = get_destination_registry()
    active = get_active_signal_type_id()
    platforms = get_mention_parser().platforms_in_text(text)
    matched: list[str] = []

    for token in tokens:
        if token in source_registry.source_ids:
            matched.append(token)
        elif token == active:
            matched.append(token)
        elif token in destination_registry.destination_ids:
            platform = connector_to_platform(token)
            if platform and platform not in platforms:
                platforms.append(platform)

    return dedupe(matched), dedupe(platforms)


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

    matched_tokens, mentioned_platforms = sanitize_scope_hints(
        get_lookup().normalize_tokens([str(token) for token in raw_tokens]),
        latest_text,
    )

    if status == "in_scope" and not matched_tokens and not mentioned_platforms:
        return fallback

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
        return finalize_intent(
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
                normalized = lookup.normalize_connector(str(item))
                if normalized and normalized != GOOGLE_CUSTOMER_MATCH:
                    picked.append(normalized)
            if picked:
                channels = picked

    return finalize_intent(
        source,
        platform_mentions,
        channels,
        signal_type,
        current["attempt"],
        latest_text,
        scope_tokens,
        scope_platforms,
    )


def _destination_compatible_with_signal(dest_id: str, signal_type: str) -> bool:
    destination_registry = get_destination_registry()
    entry = destination_registry.get_destination(dest_id)
    if entry is None:
        return False
    if not entry.signal_types:
        return signal_type == get_active_signal_type_id()
    return signal_type in entry.signal_types


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
        signal_type = intent.get("signal_type") or active
        suggested = intent["channels"]
        if not suggested and intent.get("platform_mentions"):
            suggested = resolve_platforms_to_channels(
                destination_registry,
                intent["platform_mentions"],
                "",
                signal_type,
            )
        options = []
        for destination in destination_registry.list_destinations():
            active_flag, reason = is_v1_active(destination.id)
            if active_flag and not _destination_compatible_with_signal(destination.id, signal_type):
                active_flag = False
                reason = f"Not available for {signal_type}"
            options.append({"id": destination.id, "active": active_flag, "reason": reason})
        field = {
            "suggested": suggested,
            "selected": intent["channels"] or suggested,
            "required": True,
            "multi": True,
            "platform_mentions": intent.get("platform_mentions", []),
            "options": options,
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


def build_intent_clarify_payload(intent: IntentPhase) -> dict:
    return build_clarify_payload(intent)
