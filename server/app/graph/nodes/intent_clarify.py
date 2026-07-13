from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from app.graph.handlers import (
    compose_intent_clarify_message,
    compose_intent_give_up_message,
    compose_intent_summary,
    format_intent_summary_message,
)
from app.graph.llm import get_llm
from app.graph.state import INTENT_MAX_ATTEMPTS, IntentPhase, SignalsState
from app.graph.validators import (
    build_clarify_payload,
    last_human_text,
    matched_token_ids,
    merge_intent_selection,
    with_derived_destinations,
)


async def _complete_with_summary(
    intent: IntentPhase,
    user_name: str | None,
) -> dict:
    """Derive destinations, mark complete, emit intent_summary → router END."""
    llm = get_llm()
    completed = with_derived_destinations(intent)
    summary_text = await compose_intent_summary(llm, completed, user_name)
    content = format_intent_summary_message(completed, summary_text)
    return {"intent": completed, "messages": [AIMessage(content=content)]}


async def intent_clarify_node(state: SignalsState) -> dict:
    """One-field HITL loop; when human fields filled → derive destinations + summary."""
    llm = get_llm()
    intent = state.get("intent")
    if not intent:
        return {}

    if intent.get("attempt", 0) > INTENT_MAX_ATTEMPTS:
        text = await compose_intent_give_up_message(llm, state.get("user_name"))
        return {"messages": [AIMessage(content=text)]}

    # Human fields filled (from capture or prior HITL) — no interrupt; derive + summary.
    if intent.get("open_question") is None:
        return await _complete_with_summary(intent, state.get("user_name"))

    messages = state["messages"]
    scope = state.get("scope") or {}
    scope_tokens = matched_token_ids(scope)
    scope_platforms = scope.get("mentioned_platforms", [])
    latest_text = last_human_text(messages)

    payload = build_clarify_payload(intent)
    selection = interrupt(payload)

    merged = merge_intent_selection(selection, intent, latest_text, scope_tokens, scope_platforms)

    if merged.get("open_question") is None:
        merged["attempt"] = intent["attempt"]
        return await _complete_with_summary(merged, state.get("user_name"))

    next_attempt = intent.get("attempt", 1) + 1
    merged["attempt"] = next_attempt

    if next_attempt > INTENT_MAX_ATTEMPTS:
        text = await compose_intent_give_up_message(llm, state.get("user_name"))
        merged["status"] = "partial"
        return {"intent": merged, "messages": [AIMessage(content=text)]}

    retry_text = await compose_intent_clarify_message(llm, messages, merged, scope_tokens)
    return {"intent": merged, "messages": [AIMessage(content=retry_text)]}
