from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from app.graph.handlers.common import SILENT_LLM_CONFIG, parse_json_response
from app.graph.prompts.check_channels import build_check_channels_intro_prompt

logger = logging.getLogger(__name__)


def _fallback_intro(destination_labels: list[str]) -> str:
    if not destination_labels:
        return (
            "Before we map anything, let's get all your destinations connected. "
            "I'll check what's missing and connect them in order."
        )
    if len(destination_labels) == 1:
        name = destination_labels[0]
        return (
            f"Before we map anything, let's get your destination connected. "
            f"You picked {name} — I'll check it and connect if it's missing."
        )
    names = " and ".join(
        [", ".join(destination_labels[:-1]), destination_labels[-1]]
        if len(destination_labels) > 2
        else destination_labels
    )
    return (
        "Before we map anything, let's get all your destinations connected. "
        f"You picked {names} — I'll check both and connect any that are missing, in order."
        if len(destination_labels) == 2
        else (
            "Before we map anything, let's get all your destinations connected. "
            f"You picked {names} — I'll check them and connect any that are missing, in order."
        )
    )


def _fallback_next(first_pending_label: str | None, destination_labels: list[str]) -> str:
    if not first_pending_label:
        return "All selected destinations look ready — confirm to continue."
    others = [label for label in destination_labels if label != first_pending_label]
    if others:
        joined = " and ".join(others) if len(others) <= 2 else ", ".join(others)
        return (
            f"I'll connect {first_pending_label} now on the existing screen, "
            f"then we map {first_pending_label} and {joined} together in one step."
        )
    return (
        f"I'll connect {first_pending_label} now on the existing screen, "
        "then we can continue to mapping."
    )


async def compose_check_channels_messages(
    llm: ChatOpenAI,
    *,
    destination_labels: list[str],
    first_pending_label: str | None,
) -> tuple[str, str]:
    """Return ``(intro, next)`` chat lines for Visit A.

    Falls back to deterministic copy when the LLM response is missing/invalid.
    """
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=build_check_channels_intro_prompt(
                        destination_labels=destination_labels,
                        first_pending_label=first_pending_label,
                    )
                ),
            ],
            config=SILENT_LLM_CONFIG,
        )
        content = response.content
        if not isinstance(content, str):
            content = str(content)
        parsed = parse_json_response(content)
    except Exception:
        logger.exception("compose_check_channels_messages: LLM call failed")
        return (
            _fallback_intro(destination_labels),
            _fallback_next(first_pending_label, destination_labels),
        )

    if not parsed:
        return (
            _fallback_intro(destination_labels),
            _fallback_next(first_pending_label, destination_labels),
        )

    intro_raw = parsed.get("intro")
    next_raw = parsed.get("next")
    intro = intro_raw.strip() if isinstance(intro_raw, str) and intro_raw.strip() else None
    next_line = next_raw.strip() if isinstance(next_raw, str) and next_raw.strip() else None
    if intro is None or next_line is None:
        return (
            _fallback_intro(destination_labels),
            _fallback_next(first_pending_label, destination_labels),
        )
    return intro, next_line
