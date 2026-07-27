"""Registry-driven source + destination OAuth authorize / callback / status."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_owned_project_from_query
from app.destinations import get_connector as get_destination_connector
from app.destinations import get_destination, is_supported_destination, resolve_destination
from app.destinations.exceptions import DestinationRegistryError
from app.models.connections import (
    DestinationConnection,
    DestinationOAuthPending,
    OAuthPending,
    SourceConnection,
)
from app.models.project import Project
from app.schemas.connections import (
    DestinationAuthorizeResponse,
    DestinationConnectionStatusResponse,
    DestinationMockConnectRequest,
    SourceAuthorizeResponse,
    SourceConnectionStatusResponse,
)
from app.services.destination_oauth import (
    oauth_popup_close_response as destination_oauth_popup_close_response,
)
from app.services.destination_oauth import upsert_destination_connection
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

_META_DESTINATIONS = frozenset({"meta_capi"})
_GOOGLE_DESTINATIONS = frozenset({"google_offline_conversions", "google_customer_match"})


def _resolve_source_id(source_id: str) -> str:
    """Map path/alias to registry source.id, or 404."""
    resolved = resolve_source(source_id) or source_id
    if not is_supported_source(resolved):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown source {source_id!r}",
        )
    return resolved


def _resolve_destination_id(destination_id: str) -> str:
    resolved = resolve_destination(destination_id) or destination_id
    if not is_supported_destination(resolved):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown destination {destination_id!r}",
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


def _destination_oauth_done(
    *,
    success: bool,
    destination_id: str,
    error: str | None = None,
) -> HTMLResponse:
    return destination_oauth_popup_close_response(
        success=success,
        destination_id=destination_id,
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


# ── Destinations ─────────────────────────────────────────────────────────────


@router.post(
    "/destinations/{destination_id}/authorize",
    response_model=DestinationAuthorizeResponse,
)
async def authorize_destination(
    destination_id: str,
    project: Project = Depends(get_owned_project_from_query),
    db: AsyncSession = Depends(get_db),
) -> DestinationAuthorizeResponse:
    resolved_id = _resolve_destination_id(destination_id)
    destination = get_destination(resolved_id)
    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown destination {destination_id!r}",
        )

    state = new_oauth_state()
    challenge: str | None = None
    verifier: str | None = None
    if destination.oauth.pkce:
        verifier, challenge = generate_pkce_pair()

    pending = DestinationOAuthPending(
        state=state,
        project_id=project.id,
        destination_type=resolved_id,
        pkce_verifier=verifier,
        expires_at=pending_expires_at(),
    )
    db.add(pending)
    await db.commit()

    try:
        connector = get_destination_connector(resolved_id)
        auth_url = connector.auth_url(state, challenge)
    except DestinationRegistryError as exc:
        result = await db.execute(
            select(DestinationOAuthPending).where(DestinationOAuthPending.state == state)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await db.delete(row)
            await db.commit()
        logger.warning("OAuth env missing for destination=%s: %s", resolved_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        result = await db.execute(
            select(DestinationOAuthPending).where(DestinationOAuthPending.state == state)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await db.delete(row)
            await db.commit()
        logger.exception("Failed to build auth URL for destination=%s", resolved_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start OAuth for {resolved_id}",
        ) from exc

    return DestinationAuthorizeResponse(auth_url=auth_url, state=state)


@router.get(
    "/destinations/{destination_id}/status",
    response_model=DestinationConnectionStatusResponse,
)
async def destination_connection_status(
    destination_id: str,
    project: Project = Depends(get_owned_project_from_query),
    db: AsyncSession = Depends(get_db),
) -> DestinationConnectionStatusResponse:
    resolved_id = _resolve_destination_id(destination_id)
    result = await db.execute(
        select(DestinationConnection).where(
            DestinationConnection.project_id == project.id,
            DestinationConnection.destination_type == resolved_id,
        )
    )
    connection = result.scalar_one_or_none()
    return DestinationConnectionStatusResponse(
        connected=connection is not None,
        destination_id=resolved_id,
    )


@router.get("/destinations/{destination_id}/callback")
async def destination_oauth_callback(
    destination_id: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    try:
        resolved_id = _resolve_destination_id(destination_id)
    except HTTPException:
        return _destination_oauth_done(
            success=False,
            destination_id=destination_id,
            error="unknown_destination",
        )

    destination = get_destination(resolved_id)
    if destination is None:
        return _destination_oauth_done(
            success=False,
            destination_id=resolved_id,
            error="unknown_destination",
        )

    if error:
        detail = f"{error}: {error_description}" if error_description else error
        return _destination_oauth_done(
            success=False,
            destination_id=resolved_id,
            error=detail,
        )

    if not code or not state:
        return _destination_oauth_done(
            success=False,
            destination_id=resolved_id,
            error="missing_code_or_state",
        )

    result = await db.execute(
        select(DestinationOAuthPending).where(DestinationOAuthPending.state == state)
    )
    pending = result.scalar_one_or_none()
    if pending is None:
        return _destination_oauth_done(
            success=False,
            destination_id=resolved_id,
            error="invalid_or_expired_state",
        )

    if pending.destination_type != resolved_id:
        await db.delete(pending)
        await db.commit()
        return _destination_oauth_done(
            success=False,
            destination_id=resolved_id,
            error="destination_mismatch",
        )

    expires_at = pending.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        await db.delete(pending)
        await db.commit()
        return _destination_oauth_done(
            success=False,
            destination_id=resolved_id,
            error="oauth_state_expired",
        )

    verifier = pending.pkce_verifier or None
    if verifier == "":
        verifier = None

    try:
        connector = get_destination_connector(resolved_id)
        tokens = await connector.exchange(code, verifier)
        metadata = {k: v for k, v in connector.mock_metadata().items() if k != "mock"}
        if resolved_id in _GOOGLE_DESTINATIONS:
            dry = await connector.dry_run(
                {"access_token": tokens.get("access_token", "")},
                metadata,
            )
            if not dry.passed:
                await db.delete(pending)
                await db.commit()
                return _destination_oauth_done(
                    success=False,
                    destination_id=resolved_id,
                    error=dry.detail,
                )
        await upsert_destination_connection(
            db,
            project_id=pending.project_id,
            destination_type=resolved_id,
            tokens=tokens,
            metadata=metadata,
        )
        await db.delete(pending)
        await db.commit()
    except Exception as exc:
        logger.exception("OAuth token exchange failed destination=%s", resolved_id)
        await db.rollback()
        result = await db.execute(
            select(DestinationOAuthPending).where(DestinationOAuthPending.state == state)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await db.delete(row)
            await db.commit()
        return _destination_oauth_done(
            success=False,
            destination_id=resolved_id,
            error=str(exc),
        )

    return _destination_oauth_done(success=True, destination_id=resolved_id)


@router.post(
    "/destinations/{destination_id}/mock-connect",
    response_model=DestinationConnectionStatusResponse,
)
async def mock_connect_destination(
    destination_id: str,
    body: DestinationMockConnectRequest,
    project: Project = Depends(get_owned_project_from_query),
    db: AsyncSession = Depends(get_db),
) -> DestinationConnectionStatusResponse:
    resolved_id = _resolve_destination_id(destination_id)
    connector = get_destination_connector(resolved_id)
    metadata = {**connector.mock_metadata(), **body.metadata}

    if resolved_id in _META_DESTINATIONS:
        pixel_id = (body.pixel_id or "").strip()
        access_token = (body.access_token or "").strip()
        if not pixel_id or not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pixel_id and access_token are required for Meta mock connect",
            )
        metadata["pixelId"] = pixel_id
        metadata["mock"] = True
        tokens = {
            "access_token": access_token,
            "refresh_token": "mock_refresh_token",
        }
    elif resolved_id in _GOOGLE_DESTINATIONS:
        refresh_token = (body.refresh_token or "").strip()
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refresh_token is required for Google mock connect",
            )
        used_placeholder_token = False
        try:
            tokens = await connector.refresh(refresh_token)
        except DestinationRegistryError as exc:
            logger.warning(
                "Google refresh skipped (env missing) destination=%s: %s",
                resolved_id,
                exc,
            )
            tokens = {
                "access_token": "mock_access_token",
                "refresh_token": refresh_token,
            }
            used_placeholder_token = True
        except Exception as exc:
            logger.warning("Google refresh failed destination=%s: %s", resolved_id, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Google refresh_token: {exc}",
            ) from exc
        if not tokens.get("refresh_token"):
            tokens = {**tokens, "refresh_token": refresh_token}

        # Live Ads check when we have a real access token (not env-missing placeholder).
        if not used_placeholder_token:
            dry = await connector.dry_run(
                {"access_token": str(tokens.get("access_token") or "")},
                {},  # omit mock flag so developer-token check can run
            )
            if not dry.passed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=dry.detail,
                )

        metadata["mock"] = True
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mock connect is not supported for {resolved_id!r}",
        )

    await upsert_destination_connection(
        db,
        project_id=project.id,
        destination_type=resolved_id,
        tokens=tokens,
        metadata=metadata,
    )
    await db.commit()
    return DestinationConnectionStatusResponse(
        connected=True,
        destination_id=resolved_id,
    )
