from langchain_core.messages import AIMessage

from app.graph.handlers import classify_scope, compose_scope_reply, validate_scope_json
from app.graph.llm import get_llm
from app.graph.state import SignalsState


async def scope_guard_node(state: SignalsState) -> dict:
    """Classify scope (LLM), validate in Python, compose guided reply (LLM)."""
    llm = get_llm()
    messages = state["messages"]
    user_name = state.get("user_name")

    raw = await classify_scope(llm, messages)
    scope = validate_scope_json(raw)
    reply_text = await compose_scope_reply(llm, messages, scope, user_name)

    return {
        "scope": scope,
        "messages": [AIMessage(content=reply_text)],
    }
