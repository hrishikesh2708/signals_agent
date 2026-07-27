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


class IntentPhase(TypedDict):
    source: str | None
    channels: list[str]  # product_groups (e.g. meta, google) — human field
    destinations: list[str]  # connector ids — machine-only, set after derive
    signal_type: Literal["offline_conversion"] | None
    status: Literal["complete", "partial"]  # complete only after destinations derived
    open_question: IntentOpenQuestion | None
    attempt: int
    hitl_prompted: bool  # False until ask AIMessage sent for current open_question


class SourcePhase(TypedDict):
    """Post-auth source connection + object selection (separate from intent)."""

    source_id: str
    source_label: str
    project_name: str | None
    status: Literal["connected"]
    object_name: str | None  # user selection — None until select_object resume
    recommended_object: str | None  # optional LLM hint; not a progress gate
    object_hitl_prompted: bool  # False until Visit A ask messages are sent


__all__ = [
    "CONFIDENCE_THRESHOLD",
    "GraphInput",
    "INTENT_MAX_ATTEMPTS",
    "IntentOpenQuestion",
    "IntentPhase",
    "MatchedToken",
    "ScopePhase",
    "SignalsState",
    "SourcePhase",
    "build_invoke_input",
]


class SignalsState(TypedDict):
    """Full graph state (checkpointed across turns when a checkpointer is used)."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_name: str | None
    project_id: NotRequired[str | None]  # injected from session / X-Project-Id
    scope: ScopePhase | None
    intent: IntentPhase | None
    source: NotRequired[SourcePhase | None]


class GraphInput(TypedDict):
    """Fields passed on each graph invoke (Studio, CLI, API)."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_name: NotRequired[str | None]
    project_id: NotRequired[str | None]


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
