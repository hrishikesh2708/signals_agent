from app.graph.handlers import extract_intent
from app.graph.llm import get_llm
from app.graph.state import SignalsState
from app.graph.validators import (
    build_intent_from_extract,
    last_human_text,
    matched_token_ids,
)


async def intent_capture_node(state: SignalsState) -> dict:
    """Extract source / signal_type / channels only; silent handoff to clarify."""
    llm = get_llm()
    messages = state["messages"]
    scope = state.get("scope") or {}
    scope_tokens = matched_token_ids(scope)
    scope_platforms = scope.get("mentioned_platforms", [])
    latest_text = last_human_text(messages)

    raw = await extract_intent(llm, messages, scope_tokens)
    intent = build_intent_from_extract(raw, scope_tokens, latest_text, scope_platforms)
    # No user-facing message — clarify owns HITL / derive / summary.
    return {"intent": intent}
