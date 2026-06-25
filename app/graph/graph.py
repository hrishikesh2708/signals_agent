from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes import chat_node
from app.graph.state import AgentState


def _build() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph


def build_studio_graph() -> CompiledStateGraph:
    """Compile without a checkpointer — used by ``langgraph dev`` / Studio."""
    return _build().compile(name="signals_agent")


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Compile with an optional checkpointer (InMemorySaver now, Postgres later)."""
    return _build().compile(checkpointer=checkpointer, name="signals_agent")
