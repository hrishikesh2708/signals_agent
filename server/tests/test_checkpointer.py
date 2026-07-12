"""Tests for Postgres checkpointer helpers and resume-across-restart behavior."""

from __future__ import annotations

import uuid
from typing import TypedDict

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.graph.checkpoint import delete_thread, postgres_conn_string


def test_postgres_conn_string_strips_sqlalchemy_drivers() -> None:
    assert (
        postgres_conn_string("postgresql+psycopg://signals:signals@localhost:5432/signals")
        == "postgresql://signals:signals@localhost:5432/signals"
    )
    assert postgres_conn_string("postgresql+psycopg2://u:p@host/db") == "postgresql://u:p@host/db"
    assert postgres_conn_string("postgresql://already/ok") == "postgresql://already/ok"


@pytest.mark.asyncio
async def test_delete_thread_noop_without_checkpointer() -> None:
    await delete_thread(None, "session-id")


@pytest.mark.asyncio
async def test_delete_thread_with_memory_saver() -> None:
    checkpointer = InMemorySaver()
    await delete_thread(checkpointer, "session-id")


class _CounterState(TypedDict):
    count: int


def _build_counter_graph(checkpointer: AsyncPostgresSaver):
    graph = StateGraph(_CounterState)

    def increment(state: _CounterState) -> dict:
        return {"count": state["count"] + 1}

    graph.add_node("increment", increment)
    graph.add_edge(START, "increment")
    graph.add_edge("increment", END)
    return graph.compile(checkpointer=checkpointer)


@pytest.mark.asyncio
async def test_postgres_checkpointer_resumes_after_reopen() -> None:
    """Simulates server restart: new from_conn_string + graph, same session_id thread."""
    conn_string = postgres_conn_string(settings.database_url)
    session_id = f"be7-test-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": session_id}}

    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        graph = _build_counter_graph(checkpointer)
        result = await graph.ainvoke({"count": 0}, config=config)
        assert result["count"] == 1

    # New connection / checkpointer instance — same thread_id must resume state.
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        graph = _build_counter_graph(checkpointer)
        result = await graph.ainvoke({"count": result["count"]}, config=config)
        assert result["count"] == 2
        await delete_thread(checkpointer, session_id)
