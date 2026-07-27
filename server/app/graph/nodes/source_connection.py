from __future__ import annotations

from uuid import UUID

from langchain_core.messages import AIMessage
from langgraph.types import interrupt
from sqlalchemy import select

from app.database import async_session_factory
from app.graph.state import SignalsState, SourcePhase
from app.graph.validators.source_connection import (
    build_source_connection_payload,
    format_source_connection_ack,
    parse_source_connection_resume,
)
from app.models.connections import SourceConnection
from app.models.project import Project
from app.sources import get_source, is_supported_source, resolve_source


async def _connection_status(
    project_id: UUID,
    source_id: str,
) -> tuple[bool, str | None]:
    """Return (connected, project_name) for the active project + source."""
    async with async_session_factory() as db:
        project = await db.get(Project, project_id)
        project_name = project.name if project is not None else None
        result = await db.execute(
            select(SourceConnection).where(
                SourceConnection.project_id == project_id,
                SourceConnection.source_type == source_id,
            )
        )
        connection = result.scalar_one_or_none()
        return connection is not None, project_name


def _connected_phase(
    *,
    source_id: str,
    source_label: str,
    project_name: str | None,
) -> SourcePhase:
    return {
        "source_id": source_id,
        "source_label": source_label,
        "project_name": project_name,
        "status": "connected",
        "object_name": None,
        "recommended_object": None,
        "object_hitl_prompted": False,
    }


def _success_update(
    *,
    source_id: str,
    source_label: str,
    project_name: str | None,
) -> dict:
    return {
        "source": _connected_phase(
            source_id=source_id,
            source_label=source_label,
            project_name=project_name,
        ),
        "messages": [AIMessage(content=format_source_connection_ack(source_label))],
    }


async def source_connection_node(state: SignalsState) -> dict:
    """Gate on a usable SourceConnection; interrupt only when auth is needed.

    - Connected for ``(project_id, intent.source)`` → SourcePhase + step_complete.
    - Otherwise → ``source_connection`` HITL; on resume re-check the DB.
    - After successful connect (or already connected) → SourcePhase + step_complete.
    """
    intent = state.get("intent") or {}
    raw_source = intent.get("source")
    if not raw_source:
        return {}

    source_id = resolve_source(raw_source) or raw_source
    if not is_supported_source(source_id):
        return {}

    project_id_raw = state.get("project_id")
    if not project_id_raw:
        return {}

    try:
        project_id = UUID(str(project_id_raw))
    except ValueError:
        return {}

    source = get_source(source_id)
    source_label = source.display_name if source is not None else source_id

    connected, project_name = await _connection_status(project_id, source_id)
    if connected:
        return _success_update(
            source_id=source_id,
            source_label=source_label,
            project_name=project_name,
        )

    resume = interrupt(
        build_source_connection_payload(
            source_id=source_id,
            source_label=source_label,
            project_id=str(project_id),
            project_name=project_name or "this project",
        )
    )
    parse_source_connection_resume(resume)

    connected, project_name = await _connection_status(project_id, source_id)
    if connected:
        return _success_update(
            source_id=source_id,
            source_label=source_label,
            project_name=project_name,
        )

    return {
        "messages": [
            AIMessage(
                content=(
                    f"I couldn't verify the {source_label} connection yet. "
                    "Please connect from Sources and try again."
                )
            )
        ]
    }
