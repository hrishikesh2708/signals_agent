from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes import scope_guard_node
from app.graph.state import GraphInput, SignalsState


def _build() -> StateGraph:
    graph = StateGraph(SignalsState, input_schema=GraphInput)
    graph.add_node("scope_guard", scope_guard_node)
    graph.add_edge(START, "scope_guard")
    graph.add_edge("scope_guard", END)
    return graph


def build_studio_graph() -> CompiledStateGraph:
    """Compile without a checkpointer — used by ``langgraph dev`` / Studio."""
    return _build().compile(name="signals_agent")


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Compile with an optional checkpointer (InMemorySaver now, Postgres later)."""
    return _build().compile(checkpointer=checkpointer, name="signals_agent")
