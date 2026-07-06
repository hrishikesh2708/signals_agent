from typing import Annotated, Literal

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import add_messages
from typing_extensions import NotRequired, TypedDict

INTENT_MAX_ATTEMPTS = 3

IntentOpenQuestion = Literal["source", "signal_type", "channels"]


class ScopePhase(TypedDict):
    status: Literal["in_scope", "out_of_scope"]
    reply_kind: Literal["ack", "greeting", "redirect"]
    matched_tokens: list[str]
    mentioned_platforms: list[str]


class IntentPhase(TypedDict):
    source: str | None
    platform_mentions: list[str]
    channels: list[str]
    signal_type: Literal["offline_conversion"] | None
    status: Literal["complete", "partial"]
    open_question: IntentOpenQuestion | None
    attempt: int
    missing: list[str]


__all__ = [
    "GraphInput",
    "INTENT_MAX_ATTEMPTS",
    "IntentOpenQuestion",
    "IntentPhase",
    "ScopePhase",
    "SignalsState",
    "build_invoke_input",
]


class SignalsState(TypedDict):
    """Full graph state (checkpointed across turns when a checkpointer is used)."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_name: str | None
    scope: ScopePhase | None
    intent: IntentPhase | None


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
