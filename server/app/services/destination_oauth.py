"""Shared helpers for destination OAuth authorize / callback / status / mock."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connections import DestinationConnection
from app.services.source_oauth import (
    generate_pkce_pair,
    new_oauth_state,
    pending_expires_at,
)

__all__ = [
    "generate_pkce_pair",
    "new_oauth_state",
    "oauth_popup_close_response",
    "pending_expires_at",
    "upsert_destination_connection",
]


async def upsert_destination_connection(
    db: AsyncSession,
    *,
    project_id: UUID,
    destination_type: str,
    tokens: dict,
    metadata: dict | None = None,
) -> DestinationConnection:
    """Upsert tokens + metadata for project+destination. Caller commits."""
    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("tokens must include a non-empty access_token")

    refresh_token = tokens.get("refresh_token")
    if not isinstance(refresh_token, str):
        refresh_token = ""

    meta = dict(metadata) if metadata else {}

    result = await db.execute(
        select(DestinationConnection).where(
            DestinationConnection.project_id == project_id,
            DestinationConnection.destination_type == destination_type,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = DestinationConnection(
            project_id=project_id,
            destination_type=destination_type,
            access_token=access_token,
            refresh_token=refresh_token,
            metadata_=meta,
        )
        db.add(connection)
    else:
        connection.access_token = access_token
        connection.refresh_token = refresh_token
        connection.metadata_ = meta
    await db.flush()
    return connection


def oauth_popup_close_response(
    *,
    success: bool,
    destination_id: str,
    error: str | None = None,
) -> HTMLResponse:
    """HTML page that postMessages the opener and closes."""
    payload = json.dumps(
        {
            "type": "oauth_complete",
            "success": success,
            "destination_id": destination_id,
            "error": error or "",
        }
    )
    html = f"""<!DOCTYPE html>
<html>
<body>
<script>
  if (window.opener) {{
    window.opener.postMessage({payload}, '*');
  }}
  window.close();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
