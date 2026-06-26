from langchain_core.messages import HumanMessage

from app.graph.graph import build_studio_graph
from app.graph.state import build_invoke_input


def test_build_studio_graph_compiles() -> None:
    graph = build_studio_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "scope_guard" in node_names
    assert "__start__" in node_names
    assert "__end__" in node_names


def test_build_studio_graph_name() -> None:
    graph = build_studio_graph()
    assert graph.name == "signals_agent"


def test_build_invoke_input_without_user_name() -> None:
    payload = build_invoke_input("hello")
    assert len(payload["messages"]) == 1
    assert isinstance(payload["messages"][0], HumanMessage)
    assert payload["messages"][0].content == "hello"
    assert "user_name" not in payload


def test_build_invoke_input_with_user_name() -> None:
    payload = build_invoke_input("hello", user_name="Hrishikesh")
    assert payload["user_name"] == "Hrishikesh"
