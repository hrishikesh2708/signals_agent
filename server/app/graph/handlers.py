import json
import logging
import re

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.destinations import get_destination_registry
from app.graph.prompts import (
    build_intent_clarify_prompt,
    build_intent_extract_prompt,
    build_intent_give_up_prompt,
    build_intent_summary_prompt,
    build_scope_classify_prompt,
    build_scope_compose_prompt,
    intent_fallback_give_up,
    intent_fallback_summary,
    scope_fallback_reply,
)
from app.graph.state import INTENT_MAX_ATTEMPTS, IntentPhase, ScopePhase
from app.internal.signal_type import format_signal_type_lines, get_active_signal_type_id
from app.sources import get_source_registry

logger = logging.getLogger(__name__)

ACTIVE_SIGNAL_TYPE = get_active_signal_type_id()


def format_source_lines() -> str:
    lines = [
        f'  "{source.id}"  ({source.display_name})'
        for source in get_source_registry().list_sources()
    ]
    return "\n".join(lines) or "  (none)"


def format_destination_lines() -> str:
    lines: list[str] = []
    for entry in get_destination_registry().list_destinations():
        line = f'  "{entry.id}"  ({entry.channel_display_name})'
        extras: list[str] = []
        if entry.product_group:
            extras.append(f"group={entry.product_group}")
            extras.append(f"group_default={entry.group_default}")
        if entry.disambiguators:
            extras.append(f"pick_when={list(entry.disambiguators)}")
        if entry.signal_types:
            extras.append(f"signal_types={list(entry.signal_types)}")
        if extras:
            line += f"  [{', '.join(extras)}]"
        lines.append(line)
    return "\n".join(lines) or "  (none)"


def format_intent_dest_lines() -> str:
    return format_destination_lines()


def _parse_json_response(content: str) -> dict | None:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM response: failed to parse JSON")
        return None

    if not isinstance(parsed, dict):
        return None
    return parsed


def _display_name(user_name: str | None) -> str:
    return user_name.strip() if user_name and user_name.strip() else "there"


async def classify_scope(llm: ChatOpenAI, messages: list[BaseMessage]) -> dict | None:
    prompt = build_scope_classify_prompt(
        format_source_lines(),
        format_destination_lines(),
        format_signal_type_lines(),
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


async def extract_intent(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    scope_tokens: list[str],
) -> dict | None:
    prompt = build_intent_extract_prompt(
        format_source_lines(),
        format_intent_dest_lines(),
        scope_tokens,
    )
    response = await llm.ainvoke([SystemMessage(content=prompt), *messages])
    content = response.content
    if not isinstance(content, str):
        content = str(content)
    return _parse_json_response(content)


async def compose_intent_summary(
    llm: ChatOpenAI,
    intent: IntentPhase,
    user_name: str | None,
) -> str:
    name = _display_name(user_name)
    source = intent["source"] or "your source"
    channels = intent["channels"]
    signal_type = intent["signal_type"] or ACTIVE_SIGNAL_TYPE
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=build_intent_summary_prompt(source, channels, signal_type, name)
                ),
            ]
        )
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        logger.exception("compose_intent_summary: LLM call failed")

    return intent_fallback_summary(name, source, channels)


async def compose_intent_clarify_message(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    intent: IntentPhase,
    scope_tokens: list[str],
) -> str:
    open_question = intent.get("open_question") or "source"
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=build_intent_clarify_prompt(
                        intent["source"],
                        intent.get("platform_mentions", []),
                        intent["channels"],
                        intent["signal_type"],
                        open_question,
                        scope_tokens,
                    )
                ),
                *messages,
            ]
        )
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        logger.exception("compose_intent_clarify_message: LLM call failed")

    fallbacks = {
        "source": "Which CRM source should we connect?",
        "signal_type": "v1 supports offline conversions only — please confirm the signal type in the picker.",
        "channels": "Which ad destinations should we send to? Pick them in the picker.",
    }
    return fallbacks.get(open_question, "Please confirm the next setup detail in the picker.")


async def compose_intent_give_up_message(
    llm: ChatOpenAI,
    user_name: str | None,
) -> str:
    name = _display_name(user_name)
    try:
        response = await llm.ainvoke(
            [SystemMessage(content=build_intent_give_up_prompt(name, INTENT_MAX_ATTEMPTS))]
        )
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        logger.exception("compose_intent_give_up_message: LLM call failed")

    return intent_fallback_give_up(name)
