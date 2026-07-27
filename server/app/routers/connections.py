"""Registry-driven source OAuth authorize / callback / status."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_owned_project_from_query
from app.models.connections import OAuthPending, SourceConnection
from app.models.project import Project
from app.schemas.connections import SourceAuthorizeResponse, SourceConnectionStatusResponse
from app.services.source_oauth import (
    generate_pkce_pair,
    new_oauth_state,
    oauth_popup_close_response,
    pending_expires_at,
    upsert_source_connection,
)
from app.sources import get_connector, get_source, is_supported_source, resolve_source
from app.sources.exceptions import SourceRegistryError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


def _resolve_source_id(source_id: str) -> str:
    """Map path/alias to registry source.id, or 404."""
    resolved = resolve_source(source_id) or source_id
    if not is_supported_source(resolved):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown source {source_id!r}",
        )
    return resolved


def _oauth_done(
    *,
    success: bool,
    source_id: str,
    error: str | None = None,
) -> HTMLResponse:
    return oauth_popup_close_response(
        success=success,
        source_id=source_id,
        error=error,
    )


@router.post(
    "/sources/{source_id}/authorize",
    response_model=SourceAuthorizeResponse,
)
async def authorize_source(
    source_id: str,
    project: Project = Depends(get_owned_project_from_query),
    db: AsyncSession = Depends(get_db),
) -> SourceAuthorizeResponse:
    resolved_id = _resolve_source_id(source_id)
    source = get_source(resolved_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown source {source_id!r}",
        )

    state = new_oauth_state()
    challenge: str | None = None
    verifier = ""
    if source.oauth.pkce:
        verifier, challenge = generate_pkce_pair()

    pending = OAuthPending(
        state=state,
        project_id=project.id,
        source_type=resolved_id,
        pkce_verifier=verifier,
        expires_at=pending_expires_at(),
    )
    db.add(pending)
    await db.commit()

    try:
        connector = get_connector(resolved_id)
        auth_url = connector.auth_url(state, challenge)
    except SourceRegistryError as exc:
        result = await db.execute(select(OAuthPending).where(OAuthPending.state == state))
        row = result.scalar_one_or_none()
        if row is not None:
            await db.delete(row)
            await db.commit()
        logger.warning("OAuth env missing for source=%s: %s", resolved_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        result = await db.execute(select(OAuthPending).where(OAuthPending.state == state))
        row = result.scalar_one_or_none()
        if row is not None:
            await db.delete(row)
            await db.commit()
        logger.exception("Failed to build auth URL for source=%s", resolved_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start OAuth for {resolved_id}",
        ) from exc

    return SourceAuthorizeResponse(auth_url=auth_url, state=state)


@router.get("/sources/{source_id}/status", response_model=SourceConnectionStatusResponse)
async def source_connection_status(
    source_id: str,
    project: Project = Depends(get_owned_project_from_query),
    db: AsyncSession = Depends(get_db),
) -> SourceConnectionStatusResponse:
    resolved_id = _resolve_source_id(source_id)
    result = await db.execute(
        select(SourceConnection).where(
            SourceConnection.project_id == project.id,
            SourceConnection.source_type == resolved_id,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        return SourceConnectionStatusResponse(
            connected=False,
            instance_url=None,
            source_id=resolved_id,
        )
    return SourceConnectionStatusResponse(
        connected=True,
        instance_url=connection.instance_url,
        source_id=resolved_id,
    )


@router.get("/sources/{source_id}/callback")
async def source_oauth_callback(
    source_id: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    try:
        resolved_id = _resolve_source_id(source_id)
    except HTTPException:
        return _oauth_done(success=False, source_id=source_id, error="unknown_source")

    source = get_source(resolved_id)
    if source is None:
        return _oauth_done(success=False, source_id=resolved_id, error="unknown_source")

    if error:
        detail = f"{error}: {error_description}" if error_description else error
        return _oauth_done(success=False, source_id=resolved_id, error=detail)

    if not code or not state:
        return _oauth_done(
            success=False,
            source_id=resolved_id,
            error="missing_code_or_state",
        )

    result = await db.execute(select(OAuthPending).where(OAuthPending.state == state))
    pending = result.scalar_one_or_none()
    if pending is None:
        return _oauth_done(
            success=False,
            source_id=resolved_id,
            error="invalid_or_expired_state",
        )

    if pending.source_type != resolved_id:
        await db.delete(pending)
        await db.commit()
        return _oauth_done(success=False, source_id=resolved_id, error="source_mismatch")

    expires_at = pending.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        await db.delete(pending)
        await db.commit()
        return _oauth_done(
            success=False,
            source_id=resolved_id,
            error="oauth_state_expired",
        )

    verifier = pending.pkce_verifier or None
    if verifier == "":
        verifier = None

    try:
        connector = get_connector(resolved_id)
        tokens = await connector.exchange(code, verifier)
        await upsert_source_connection(
            db,
            project_id=pending.project_id,
            source=source,
            tokens=tokens,
        )
        await db.delete(pending)
        await db.commit()
    except Exception as exc:
        logger.exception("OAuth token exchange failed source=%s", resolved_id)
        await db.rollback()
        result = await db.execute(select(OAuthPending).where(OAuthPending.state == state))
        row = result.scalar_one_or_none()
        if row is not None:
            await db.delete(row)
            await db.commit()
        return _oauth_done(success=False, source_id=resolved_id, error=str(exc))

    return _oauth_done(success=True, source_id=resolved_id)
