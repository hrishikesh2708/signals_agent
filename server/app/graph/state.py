from typing import Annotated, Literal

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import add_messages
from typing_extensions import NotRequired, TypedDict

INTENT_MAX_ATTEMPTS = 3
CONFIDENCE_THRESHOLD = 0.7

IntentOpenQuestion = Literal["source", "signal_type", "channels"]


class MatchedToken(TypedDict):
    raw: str
    id: str
    display_name: str
    confidence: float


class ScopePhase(TypedDict):
    status: Literal["in_scope", "out_of_scope"]
    reply_kind: Literal["ack", "greeting", "redirect"]
    matched_tokens: list[MatchedToken]
    mentioned_platforms: list[str]


class IntentPhase(TypedDict):
    source: str | None
    platform_mentions: list[str]
    channels: list[str]  # product_groups (e.g. meta, google) — human field
    destinations: list[str]  # connector ids — machine-only, set after derive
    signal_type: Literal["offline_conversion"] | None
    status: Literal["complete", "partial"]  # complete only after destinations derived
    open_question: IntentOpenQuestion | None
    attempt: int
    missing: list[str]


__all__ = [
    "CONFIDENCE_THRESHOLD",
    "GraphInput",
    "INTENT_MAX_ATTEMPTS",
    "IntentOpenQuestion",
    "IntentPhase",
    "MatchedToken",
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
