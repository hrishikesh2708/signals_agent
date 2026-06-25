from langgraph.graph import MessagesState

__all__ = ["AgentState"]

# Alias for clarity; extend with custom fields as the graph grows.
AgentState = MessagesState
