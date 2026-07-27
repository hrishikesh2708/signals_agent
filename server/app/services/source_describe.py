"""Validate a CRM object exists via the existing connector describe APIs."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select

from app.database import async_session_factory
from app.models.connections import SourceConnection
from app.sources import SourceAuthError, get_connector, get_source_registry

logger = logging.getLogger(__name__)


async def object_exists_via_describe(
    project_id: UUID,
    source_id: str,
    object_name: str,
) -> bool:
    """Return True when ``describe_object`` succeeds for the connected source.

    Loads ``SourceConnection`` tokens, calls the existing registry describe.
    On ``SourceAuthError``, refreshes the access token once and retries.
    Any other failure is treated as the object not being usable.
    """
    async with async_session_factory() as db:
        result = await db.execute(
            select(SourceConnection).where(
                SourceConnection.project_id == project_id,
                SourceConnection.source_type == source_id,
            )
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            logger.warning(
                "object_exists_via_describe: no connection for project=%s source=%s",
                project_id,
                source_id,
            )
            return False

        registry = get_source_registry()
        try:
            await registry.describe_object(
                source_id,
                connection.instance_url,
                connection.access_token,
                object_name,
            )
            return True
        except SourceAuthError:
            if not connection.refresh_token:
                logger.warning(
                    "object_exists_via_describe: auth failed and no refresh token "
                    "source=%s object=%s",
                    source_id,
                    object_name,
                )
                return False
            try:
                connector = get_connector(source_id)
                tokens = await connector.refresh(connection.refresh_token)
                new_access = tokens.get("access_token")
                if not isinstance(new_access, str) or not new_access:
                    return False
                connection.access_token = new_access
                if isinstance(tokens.get("refresh_token"), str) and tokens["refresh_token"]:
                    connection.refresh_token = tokens["refresh_token"]
                if isinstance(tokens.get("instance_url"), str) and tokens["instance_url"]:
                    connection.instance_url = tokens["instance_url"]
                await db.commit()

                await registry.describe_object(
                    source_id,
                    connection.instance_url,
                    connection.access_token,
                    object_name,
                )
                return True
            except Exception:
                logger.exception(
                    "object_exists_via_describe: refresh/retry failed "
                    "source=%s object=%s",
                    source_id,
                    object_name,
                )
                return False
        except Exception:
            logger.exception(
                "object_exists_via_describe: describe failed source=%s object=%s",
                source_id,
                object_name,
            )
            return False
