import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.graph.handlers.catalogs import (
    format_channel_lines,
    format_signal_type_lines,
    format_source_lines,
)
from app.graph.handlers.common import display_name, parse_json_response
from app.graph.prompts import (
    build_scope_classify_prompt,
    build_scope_compose_prompt,
    scope_fallback_reply,
)
from app.graph.state import ScopePhase

logger = logging.getLogger(__name__)


async def classify_scope(llm: ChatOpenAI, latest_text: str) -> dict | None:
    prompt = build_scope_classify_prompt(
        format_source_lines(),
        format_channel_lines(),
        format_signal_type_lines(),
    )
    response = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=latest_text)])
    content = response.content
    if not isinstance(content, str):
        content = str(content)
    return parse_json_response(content)


async def compose_scope_reply(
    llm: ChatOpenAI,
    latest_text: str,
    scope: ScopePhase,
    user_name: str | None,
) -> str:
    name = display_name(user_name)
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=build_scope_compose_prompt(scope, name)),
                HumanMessage(content=latest_text),
            ]
        )
        content = response.content
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        logger.exception("compose_scope_reply: LLM call failed")

    return scope_fallback_reply(scope["reply_kind"], name)
