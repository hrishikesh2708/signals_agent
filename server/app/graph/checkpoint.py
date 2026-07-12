"""Postgres checkpointer helpers for LangGraph thread lifecycle."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver

_SQLALCHEMY_DRIVER_PREFIXES = (
    "postgresql+psycopg://",
    "postgresql+psycopg2://",
    "postgresql+asyncpg://",
)


def postgres_conn_string(database_url: str) -> str:
    """Convert a SQLAlchemy Postgres URL to a psycopg conninfo string."""
    for prefix in _SQLALCHEMY_DRIVER_PREFIXES:
        if database_url.startswith(prefix):
            return "postgresql://" + database_url.removeprefix(prefix)
    return database_url


async def delete_thread(checkpointer: BaseCheckpointSaver | None, session_id: str) -> None:
    """Best-effort delete of LangGraph checkpoints for an agent session thread."""
    if checkpointer is None:
        return
    try:
        await checkpointer.adelete_thread(session_id)
    except Exception:
        # Older checkpointer versions may not support delete — best effort.
        pass
