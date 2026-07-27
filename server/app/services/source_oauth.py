"""Shared helpers for source OAuth authorize / callback / status."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connections import OAuthPending, SourceConnection
from app.sources.spec import Source

OAUTH_PENDING_TTL = timedelta(minutes=10)


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for S256 PKCE."""
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


def new_oauth_state() -> str:
    """Opaque CSRF state for the OAuth round-trip (not agent/session state)."""
    return secrets.token_urlsafe(32)


def pending_expires_at(*, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + OAUTH_PENDING_TTL


def instance_url_from_tokens(source: Source, tokens: dict) -> str:
    """Resolve API host: token fields first, then YAML oauth.default_instance_url."""
    if tokens.get("instance_url"):
        return str(tokens["instance_url"]).rstrip("/")
    if tokens.get("api_domain"):
        domain = str(tokens["api_domain"]).rstrip("/")
        if domain.startswith("http://") or domain.startswith("https://"):
            return domain
        return f"https://{domain}"
    default = source.oauth.default_instance_url
    if default:
        return default.rstrip("/")
    raise ValueError(
        f"Token response for {source.id!r} missing instance_url/api_domain "
        "and oauth.default_instance_url is not set in YAML"
    )


async def upsert_source_connection(
    db: AsyncSession,
    *,
    project_id: UUID,
    source: Source,
    tokens: dict,
) -> SourceConnection:
    """Upsert tokens for project+source. Caller is responsible for commit."""
    instance_url = instance_url_from_tokens(source, tokens)
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")

    result = await db.execute(
        select(SourceConnection).where(
            SourceConnection.project_id == project_id,
            SourceConnection.source_type == source.id,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = SourceConnection(
            project_id=project_id,
            source_type=source.id,
            access_token=access_token,
            refresh_token=refresh_token,
            instance_url=instance_url,
        )
        db.add(connection)
    else:
        connection.access_token = access_token
        connection.refresh_token = refresh_token
        connection.instance_url = instance_url
    await db.flush()
    return connection


def oauth_popup_close_response(
    *,
    success: bool,
    source_id: str,
    error: str | None = None,
) -> HTMLResponse:
    """HTML page that postMessages the opener and closes (agentic-workspace pattern)."""
    payload = json.dumps(
        {
            "type": "oauth_complete",
            "success": success,
            "source_id": source_id,
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
