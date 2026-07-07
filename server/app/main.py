"""CLI entrypoint for local graph invocation with in-memory checkpointing."""

import argparse
import asyncio
import json
import sys
import uuid

from langgraph.checkpoint.memory import InMemorySaver

from app.config import configure_langsmith, configure_logging, settings
from app.graph.graph import build_graph
from app.graph.state import build_invoke_input


async def run(
    message: str,
    thread_id: str,
    user_name: str | None = None,
    *,
    dump_state: bool = False,
) -> None:
    configure_logging()
    configure_langsmith()

    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.", file=sys.stderr)
        sys.exit(1)

    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    effective_user_name = user_name if user_name is not None else settings.signals_default_user_name
    payload = build_invoke_input(message, user_name=effective_user_name)

    result = await graph.ainvoke(payload, config=config)

    if dump_state:
        print(json.dumps(_state_for_display(result), indent=2))
        return

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = getattr(last, "content", str(last))
        print(content)
    else:
        print("(no response)")


def _state_for_display(state: dict) -> dict:
    displayed = {
        "user_name": state.get("user_name"),
        "scope": state.get("scope"),
        "messages": [],
    }
    for message in state.get("messages", []):
        role = getattr(message, "type", message.__class__.__name__.replace("Message", "").lower())
        content = getattr(message, "content", str(message))
        displayed["messages"].append({"role": role, "content": content})
    return displayed


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke the Signals LangGraph agent locally.")
    parser.add_argument("--message", "-m", required=True, help="User message to send")
    parser.add_argument(
        "--thread-id",
        "-t",
        default=None,
        help="Thread ID for multi-turn conversations (default: random UUID)",
    )
    parser.add_argument(
        "--user-name",
        "-u",
        default=None,
        help="User name for personalized replies (overrides SIGNALS_DEFAULT_USER_NAME)",
    )
    parser.add_argument(
        "--dump-state",
        action="store_true",
        help="Print full merged graph state as JSON instead of only the last reply",
    )
    args = parser.parse_args()
    thread_id = args.thread_id or str(uuid.uuid4())
    asyncio.run(
        run(
            args.message,
            thread_id,
            args.user_name,
            dump_state=args.dump_state,
        )
    )


if __name__ == "__main__":
    main()
