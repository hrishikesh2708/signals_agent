from app.graph.graph import build_studio_graph


def test_build_studio_graph_compiles() -> None:
    graph = build_studio_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "chat" in node_names
    assert "__start__" in node_names
    assert "__end__" in node_names


def test_build_studio_graph_name() -> None:
    graph = build_studio_graph()
    assert graph.name == "signals_agent"
