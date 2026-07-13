from langchain_core.messages import AIMessage

from app.graph.handlers import classify_scope, compose_scope_reply
from app.graph.llm import get_llm
from app.graph.state import SignalsState
from app.graph.validators import last_human_text, validate_scope_json


async def scope_guard_node(state: SignalsState) -> dict:
    """Classify scope (LLM), validate in Python, compose guided reply (LLM)."""
    llm = get_llm()
    messages = state["messages"]
    user_name = state.get("user_name")
    latest_text = last_human_text(messages)

    raw = await classify_scope(llm, latest_text)
    scope = validate_scope_json(raw, latest_text)
    reply_text = await compose_scope_reply(llm, latest_text, scope, user_name)

    return {
        "scope": scope,
        "messages": [AIMessage(content=reply_text)],
    }
