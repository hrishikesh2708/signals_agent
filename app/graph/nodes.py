from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState

from app.config import settings


def chat_node(state: MessagesState) -> dict[str, list]:
    """Single LLM node: respond to the conversation history."""
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key or None,
        temperature=0,
    )
    response = llm.invoke(state["messages"])
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response))
    return {"messages": [response]}
