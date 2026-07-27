from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes import (
    intent_capture_node,
    intent_clarify_node,
    scope_guard_node,
    select_object_node,
    source_connection_node,
)
from app.graph.routers import (
    route_after_intent_capture,
    route_after_intent_clarify,
    route_after_scope_guard,
    route_after_select_object,
    route_after_source_connection,
)
from app.graph.state import GraphInput, SignalsState


def _build() -> StateGraph:
    graph = StateGraph(SignalsState, input_schema=GraphInput)
    graph.add_node("scope_guard", scope_guard_node)
    graph.add_node("intent_capture", intent_capture_node)
    graph.add_node("intent_clarify", intent_clarify_node)
    graph.add_node("source_connection", source_connection_node)
    graph.add_node("select_object", select_object_node)

    graph.add_edge(START, "scope_guard")
    graph.add_conditional_edges(
        "scope_guard",
        route_after_scope_guard,
        {
            "intent_capture": "intent_capture",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "intent_capture",
        route_after_intent_capture,
        {
            "intent_clarify": "intent_clarify",
        },
    )
    graph.add_conditional_edges(
        "intent_clarify",
        route_after_intent_clarify,
        {
            "intent_clarify": "intent_clarify",
            "source_connection": "source_connection",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "source_connection",
        route_after_source_connection,
        {
            "select_object": "select_object",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "select_object",
        route_after_select_object,
        {
            "select_object": "select_object",
            "__end__": END,
        },
    )
    return graph


def build_studio_graph() -> CompiledStateGraph:
    """Compile without a checkpointer — used by ``langgraph dev`` / Studio."""
    return _build().compile(name="signals_agent")


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Compile with an optional checkpointer (Postgres in FastAPI, InMemory in CLI)."""
    return _build().compile(checkpointer=checkpointer, name="signals_agent")
