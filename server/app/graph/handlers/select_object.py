from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from app.graph.handlers.common import SILENT_LLM_CONFIG, parse_json_response
from app.graph.prompts.select_object import build_select_object_suggest_prompt
from app.graph.validators.select_object import validate_recommended

logger = logging.getLogger(__name__)


async def compose_object_suggestion(
    llm: ChatOpenAI,
    *,
    source_label: str,
    signal_type: str | None,
    project_name: str | None,
    options: list[str],
) -> tuple[str | None, str | None]:
    """Ask the LLM to pick a recommended object from options.

    Returns ``(recommended, rationale)``. Both are None when the response is
    missing, unparsable, or ``recommended`` is not an exact option member.
    Never invents a fallback object.
    """
    if not options:
        return None, None

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=build_select_object_suggest_prompt(
                        source_label=source_label,
                        signal_type=signal_type,
                        project_name=project_name,
                        options=options,
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
        logger.exception("compose_object_suggestion: LLM call failed")
        return None, None

    if not parsed:
        return None, None

    recommended = validate_recommended(parsed.get("recommended"), options)
    rationale_raw = parsed.get("rationale")
    rationale = (
        rationale_raw.strip()
        if isinstance(rationale_raw, str) and rationale_raw.strip()
        else None
    )

    if recommended is None or rationale is None:
        logger.warning(
            "compose_object_suggestion: rejecting suggestion recommended=%r rationale=%r",
            parsed.get("recommended"),
            rationale_raw if isinstance(rationale_raw, str) else rationale_raw,
        )
        return None, None

    return recommended, rationale
