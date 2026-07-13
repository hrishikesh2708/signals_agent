import json
import logging

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.destinations import get_destination_registry
from app.graph.handlers.catalogs import (
    format_channel_lines,
    format_signal_type_lines,
    format_source_lines,
)
from app.graph.handlers.common import display_name, parse_json_response
from app.graph.prompts import (
    build_intent_clarify_prompt,
    build_intent_extract_prompt,
    build_intent_give_up_prompt,
    build_intent_summary_prompt,
    intent_fallback_give_up,
    intent_fallback_summary,
)
from app.graph.state import INTENT_MAX_ATTEMPTS, IntentPhase
from app.internal.signal_type import get_active_signal_type_id, get_signal_type
from app.sources import get_source_registry

logger = logging.getLogger(__name__)

ACTIVE_SIGNAL_TYPE = get_active_signal_type_id()


async def extract_intent(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    scope_tokens: list[str],
) -> dict | None:
    prompt = build_intent_extract_prompt(
        format_source_lines(),
        format_channel_lines(),
        format_signal_type_lines(),
        scope_tokens,
    )
    # Last human message only — earlier turns are already reflected in scope tokens.
    latest = next(
        (message for message in reversed(messages) if message.type == "human"),
        None,
    )
    human = latest if latest is not None else HumanMessage(content="")
    response = await llm.ainvoke([SystemMessage(content=prompt), human])
    content = response.content
    if not isinstance(content, str):
        content = str(content)
    return parse_json_response(content)


async def compose_intent_summary(
    llm: ChatOpenAI,
    intent: IntentPhase,
    user_name: str | None,
) -> str:
    name = display_name(user_name)
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


def format_intent_summary_message(intent: IntentPhase, summary_text: str) -> str:
    """Package summary prose as intent_summary JSON for AgentTextBubble + IntentAckCard."""
    source_id = intent.get("source")
    source_entry = get_source_registry().get_source(source_id) if source_id else None
    signal_id = intent.get("signal_type") or ACTIVE_SIGNAL_TYPE
    signal_entry = next(
        (signal for signal in get_signal_type().signal_types if signal.id == signal_id),
        None,
    )

    destination_registry = get_destination_registry()
    destination_labels: list[str] = []
    for dest_id in intent.get("destinations") or []:
        entry = destination_registry.get_destination(dest_id)
        destination_labels.append(entry.short_label if entry else dest_id)

    if not destination_labels:
        # Fall back to channel product_group labels when derive returned empty.
        seen: set[str] = set()
        for entry in destination_registry.list_destinations():
            if (
                entry.product_group in intent.get("channels", [])
                and entry.product_group not in seen
            ):
                seen.add(entry.product_group)
                destination_labels.append(entry.short_label)

    payload = {
        "type": "intent_summary",
        "message": summary_text,
        "details": {
            "signal_type": signal_id,
            "signal_display": signal_entry.display_name if signal_entry else signal_id,
            "source": source_id,
            "source_label": source_entry.display_name if source_entry else source_id,
            "destinations": list(intent.get("destinations") or []),
            "destination_labels": destination_labels,
        },
    }
    return json.dumps(payload)


async def compose_intent_clarify_message(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    intent: IntentPhase,
    scope_hint_ids: list[str],
) -> str:
    open_question = intent.get("open_question") or "source"
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=build_intent_clarify_prompt(
                        intent["source"],
                        intent["channels"],
                        intent["signal_type"],
                        open_question,
                        scope_hint_ids,
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
    name = display_name(user_name)
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
