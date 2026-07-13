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
from app.graph.validators.intent_clarify import (
    build_clarify_payload,
    merge_intent_selection,
    scope_hint_ids,
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
    """Ask (LLM) then interrupt (static payload) per open field via hitl_prompted."""
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
    scope_hints = scope_hint_ids(state.get("scope"))

    # Visit A: emit LLM ask, then re-enter for interrupt while open_question is set.
    if not intent.get("hitl_prompted", False):
        ask_text = await compose_intent_clarify_message(llm, messages, intent, scope_hints)
        return {
            "intent": {**intent, "hitl_prompted": True},
            "messages": [AIMessage(content=ask_text)],
        }

    # Visit B: static picker interrupt → thin merge on resume.
    selection = interrupt(build_clarify_payload(intent))
    merged = merge_intent_selection(selection, intent)

    if merged.get("open_question") is None:
        merged["attempt"] = intent["attempt"]
        return await _complete_with_summary(merged, state.get("user_name"))

    next_attempt = intent.get("attempt", 1) + 1
    merged["attempt"] = next_attempt

    if next_attempt > INTENT_MAX_ATTEMPTS:
        text = await compose_intent_give_up_message(llm, state.get("user_name"))
        merged["status"] = "partial"
        return {"intent": merged, "messages": [AIMessage(content=text)]}

    # Next self-loop visit asks again (hitl_prompted already False from merge).
    return {"intent": merged}
