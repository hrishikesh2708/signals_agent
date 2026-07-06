from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from app.graph.handlers import (
    classify_scope,
    compose_intent_clarify_message,
    compose_intent_give_up_message,
    compose_intent_summary,
    compose_scope_reply,
    extract_intent,
)
from app.graph.llm import get_llm
from app.graph.state import INTENT_MAX_ATTEMPTS, SignalsState
from app.graph.validators import (
    build_intent_from_extract,
    build_intent_clarify_payload,
    last_human_text,
    merge_intent_selection,
    validate_scope_json,
)


async def scope_guard_node(state: SignalsState) -> dict:
    """Classify scope (LLM), validate in Python, compose guided reply (LLM)."""
    llm = get_llm()
    messages = state["messages"]
    user_name = state.get("user_name")

    raw = await classify_scope(llm, messages)
    latest_text = last_human_text(messages)
    scope = validate_scope_json(raw, latest_text)
    reply_text = await compose_scope_reply(llm, messages, scope, user_name)

    return {
        "scope": scope,
        "messages": [AIMessage(content=reply_text)],
    }


async def intent_capture_node(state: SignalsState) -> dict:
    """Extract setup intent; summarize when complete or hand off to clarify."""
    llm = get_llm()
    messages = state["messages"]
    scope = state.get("scope") or {}
    scope_tokens = scope.get("matched_tokens", [])
    scope_platforms = scope.get("mentioned_platforms", [])
    latest_text = last_human_text(messages)

    raw = await extract_intent(llm, messages, scope_tokens)
    intent = build_intent_from_extract(raw, scope_tokens, latest_text, scope_platforms)

    if intent["status"] == "complete":
        summary = await compose_intent_summary(llm, intent, state.get("user_name"))
        return {"intent": intent, "messages": [AIMessage(content=summary)]}

    intro = await compose_intent_clarify_message(llm, messages, intent, scope_tokens)
    return {"intent": intent, "messages": [AIMessage(content=intro)]}


async def intent_clarify_node(state: SignalsState) -> dict:
    """One focused HITL question per loop: source, signal_type, or channels."""
    llm = get_llm()
    intent = state.get("intent")
    if not intent:
        return {}

    if intent.get("attempt", 0) > INTENT_MAX_ATTEMPTS:
        text = await compose_intent_give_up_message(llm, state.get("user_name"))
        return {"messages": [AIMessage(content=text)]}

    messages = state["messages"]
    scope_tokens = (state.get("scope") or {}).get("matched_tokens", [])
    scope_platforms = (state.get("scope") or {}).get("mentioned_platforms", [])
    latest_text = last_human_text(messages)

    payload = build_intent_clarify_payload(intent)
    selection = interrupt(payload)

    merged = merge_intent_selection(selection, intent, latest_text, scope_tokens, scope_platforms)

    if merged["status"] == "complete":
        summary = await compose_intent_summary(llm, merged, state.get("user_name"))
        merged["attempt"] = intent["attempt"]
        return {"intent": merged, "messages": [AIMessage(content=summary)]}

    next_attempt = intent.get("attempt", 1) + 1
    merged["attempt"] = next_attempt

    if next_attempt > INTENT_MAX_ATTEMPTS:
        text = await compose_intent_give_up_message(llm, state.get("user_name"))
        merged["status"] = "partial"
        return {"intent": merged, "messages": [AIMessage(content=text)]}

    retry_text = await compose_intent_clarify_message(llm, messages, merged, scope_tokens)
    return {"intent": merged, "messages": [AIMessage(content=retry_text)]}
