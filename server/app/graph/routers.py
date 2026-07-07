from app.graph.state import INTENT_MAX_ATTEMPTS


def route_after_scope_guard(state: dict) -> str:
    scope = state.get("scope") or {}
    if scope.get("status") == "in_scope":
        return "intent_capture"
    return "__end__"


def route_after_intent_capture(state: dict) -> str:
    intent = state.get("intent") or {}
    if intent.get("status") == "complete":
        return "__end__"
    return "intent_clarify"


def route_after_intent_clarify(state: dict) -> str:
    intent = state.get("intent") or {}
    if intent.get("status") == "complete":
        return "__end__"
    if intent.get("attempt", 0) > INTENT_MAX_ATTEMPTS:
        return "__end__"
    return "intent_clarify"
