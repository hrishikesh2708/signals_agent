"""CLI entrypoint for local graph invocation with in-memory checkpointing."""

import argparse
import asyncio
import sys
import uuid

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.config import configure_langsmith, configure_logging, settings
from app.graph.graph import build_graph


async def run(message: str, thread_id: str) -> None:
    configure_logging()
    configure_langsmith()

    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.", file=sys.stderr)
        sys.exit(1)

    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = getattr(last, "content", str(last))
        print(content)
    else:
        print("(no response)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke the Signals LangGraph agent locally.")
    parser.add_argument("--message", "-m", required=True, help="User message to send")
    parser.add_argument(
        "--thread-id",
        "-t",
        default=None,
        help="Thread ID for multi-turn conversations (default: random UUID)",
    )
    args = parser.parse_args()
    thread_id = args.thread_id or str(uuid.uuid4())
    asyncio.run(run(args.message, thread_id))


if __name__ == "__main__":
    main()
