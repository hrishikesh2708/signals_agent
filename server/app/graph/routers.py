from app.graph.state import INTENT_MAX_ATTEMPTS


def route_after_scope_guard(state: dict) -> str:
    scope = state.get("scope") or {}
    if scope.get("status") == "in_scope":
        return "intent_capture"
    return "__end__"


def route_after_intent_capture(state: dict) -> str:
    del state  # capture always hands off; intent completeness is clarify's job
    return "intent_clarify"


def route_after_intent_clarify(state: dict) -> str:
    intent = state.get("intent") or {}
    if intent.get("status") == "complete":
        return "source_connection"
    if intent.get("attempt", 0) > INTENT_MAX_ATTEMPTS:
        return "__end__"
    # Loop only while a human field still needs HITL.
    if intent.get("open_question") is not None:
        return "intent_clarify"
    return "__end__"


def route_after_source_connection(state: dict) -> str:
    source = state.get("source") or {}
    if source.get("status") == "connected":
        return "select_object"
    return "__end__"


def route_after_select_object(state: dict) -> str:
    source = state.get("source") or {}
    if source.get("object_name"):
        return "check_channels"
    if source.get("status") == "connected":
        return "select_object"
    return "__end__"


def route_after_check_channels(state: dict) -> str:
    destinations = state.get("destinations") or {}
    if destinations.get("status") == "complete":
        return "__end__"
    source = state.get("source") or {}
    if source.get("object_name"):
        return "check_channels"
    return "__end__"
