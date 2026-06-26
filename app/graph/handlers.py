import json
import logging
import re
from functools import lru_cache

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.graph.prompts import (
    build_scope_classify_prompt,
    build_scope_compose_prompt,
    scope_fallback_reply,
)
from app.graph.sources.base import destinations, sources
from app.graph.state import ScopePhase

logger = logging.getLogger(__name__)

SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "offline_conversion": [
        "offline conversion",
        "offline conversions",
        "offline",
        "crm conversion",
        "purchase conversion",
    ],
    "web_conversion": [
        "web conversion",
        "web conversions",
        "web",
        "pixel",
        "browser event",
        "website event",
    ],
    "lead_conversion": [
        "lead conversion",
        "lead",
        "leads",
        "form fill",
        "form submission",
    ],
    "custom_audience": [
        "custom audience",
        "custom_audience",
        "audience",
        "customer match",
        "segment",
        "audience sync",
    ],
}


def _format_source_lines() -> str:
    return (
        "\n".join(f'  "{source.id}"  ({source.display_name})' for source in sources) or "  (none)"
    )


def _format_destination_lines() -> str:
    return (
        "\n".join(
            f'  "{destination.id}"  ({destination.channel_display_name})'
            for destination in destinations
        )
        or "  (none)"
    )


def _format_signal_type_lines() -> str:
    lines: list[str] = []
    for signal_id, triggers in SIGNAL_KEYWORDS.items():
        trigger_preview = ", ".join(triggers[:4])
        lines.append(f'  "{signal_id}"  (triggers include: {trigger_preview})')
    return "\n".join(lines)


@lru_cache
def _canonical_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}

    for source in sources:
        lookup[source.id.lower()] = source.id
        lookup[source.display_name.lower()] = source.id

    for destination in destinations:
        lookup[destination.id.lower()] = destination.id
        lookup[destination.channel_display_name.lower()] = destination.id
        lookup[destination.display_name.lower()] = destination.id
        for alias in destination.alias:
            lookup[alias.lower()] = destination.id

    for signal_id, triggers in SIGNAL_KEYWORDS.items():
        lookup[signal_id.lower()] = signal_id
        for trigger in triggers:
            lookup[trigger.lower()] = signal_id

    return lookup


def normalize_matched_tokens(tokens: list[str]) -> list[str]:
    """Map LLM-provided tokens to canonical source, destination, or signal ids."""
    lookup = _canonical_lookup()
    seen: set[str] = set()
    normalized: list[str] = []

    for token in tokens:
        canonical = lookup.get(token.strip().lower())
        if canonical and canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)

    return normalized


def validate_scope_json(raw: dict | None) -> ScopePhase:
    """Validate LLM classification JSON and enforce routing invariants in Python."""
    fallback: ScopePhase = {
        "status": "out_of_scope",
        "reply_kind": "redirect",
        "matched_tokens": [],
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

    matched_tokens = normalize_matched_tokens([str(token) for token in raw_tokens])

    if status == "in_scope" and not matched_tokens:
        return fallback

    return {
        "status": status,
        "reply_kind": reply_kind,
        "matched_tokens": matched_tokens,
    }


def _parse_json_response(content: str) -> dict | None:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("classify_scope: failed to parse LLM JSON")
        return None

    if not isinstance(parsed, dict):
        return None
    return parsed


def _display_name(user_name: str | None) -> str:
    return user_name.strip() if user_name and user_name.strip() else "there"


async def classify_scope(llm: ChatOpenAI, messages: list[BaseMessage]) -> dict | None:
    prompt = build_scope_classify_prompt(
        _format_source_lines(),
        _format_destination_lines(),
        _format_signal_type_lines(),
    )
    response = await llm.ainvoke([SystemMessage(content=prompt), *messages])
    content = response.content
    if not isinstance(content, str):
        content = str(content)
    return _parse_json_response(content)


async def compose_scope_reply(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    scope: ScopePhase,
    user_name: str | None,
) -> str:
    name = _display_name(user_name)
    try:
        response = await llm.ainvoke(
            [SystemMessage(content=build_scope_compose_prompt(scope, name)), *messages]
        )
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        logger.exception("compose_scope_reply: LLM call failed")

    return scope_fallback_reply(scope["reply_kind"], name)
