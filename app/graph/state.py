from typing import Annotated, Literal

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import add_messages
from typing_extensions import NotRequired, TypedDict

__all__ = [
    "GraphInput",
    "ScopePhase",
    "SignalsState",
    "build_invoke_input",
]


class ScopePhase(TypedDict):
    status: Literal["in_scope", "out_of_scope"]
    reply_kind: Literal["ack", "greeting", "redirect"]
    matched_tokens: list[str]


class SignalsState(TypedDict):
    """Full graph state (checkpointed across turns when a checkpointer is used)."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_name: str | None
    scope: ScopePhase | None


class GraphInput(TypedDict):
    """Fields passed on each graph invoke (Studio, CLI, API)."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_name: NotRequired[str | None]


def build_invoke_input(
    message: str,
    *,
    user_name: str | None = None,
) -> GraphInput:
    """Build the input payload for a single-turn invoke."""
    payload: GraphInput = {"messages": [HumanMessage(content=message)]}
    if user_name is not None:
        payload["user_name"] = user_name
    return payload
