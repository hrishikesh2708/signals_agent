import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.connections import (
    DestinationConnection,
    DestinationOAuthPending,
    OAuthPending,
    SourceConnection,
)
from app.models.project import Project
from app.models.user import User
from app.services.auth_service import hash_password


@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


async def _create_project(session: AsyncSession) -> uuid.UUID:
    user = User(
        email=f"oauth-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("securepass"),
        name="OAuth User",
    )
    session.add(user)
    await session.flush()

    project = Project(user_id=user.id, name="OAuth Project")
    session.add(project)
    await session.commit()
    return project.id


@pytest.mark.asyncio
async def test_oauth_pending_insert_and_delete(db_session: AsyncSession) -> None:
    project_id = await _create_project(db_session)
    state = f"sf-state-{uuid.uuid4()}"
    verifier = "pkce-verifier-abc123"

    pending = OAuthPending(
        state=state,
        project_id=project_id,
        source_type="salesforce",
        pkce_verifier=verifier,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    db_session.add(pending)
    await db_session.commit()

    result = await db_session.execute(select(OAuthPending).where(OAuthPending.state == state))
    row = result.scalar_one()
    assert row.project_id == project_id
    assert row.source_type == "salesforce"
    assert row.pkce_verifier == verifier

    await db_session.delete(row)
    await db_session.commit()

    result = await db_session.execute(select(OAuthPending).where(OAuthPending.state == state))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_destination_oauth_pending_allows_null_pkce(db_session: AsyncSession) -> None:
    project_id = await _create_project(db_session)
    state = f"meta-state-{uuid.uuid4()}"

    pending = DestinationOAuthPending(
        state=state,
        project_id=project_id,
        destination_type="meta_capi",
        pkce_verifier=None,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    db_session.add(pending)
    await db_session.commit()

    result = await db_session.execute(
        select(DestinationOAuthPending).where(DestinationOAuthPending.state == state)
    )
    row = result.scalar_one()
    assert row.pkce_verifier is None
    assert row.destination_type == "meta_capi"


@pytest.mark.asyncio
async def test_source_connection_unique_per_project_type(db_session: AsyncSession) -> None:
    project_id = await _create_project(db_session)

    first = SourceConnection(
        project_id=project_id,
        source_type="hubspot",
        access_token="access-1",
        refresh_token="refresh-1",
        instance_url="https://api.hubapi.com",
    )
    db_session.add(first)
    await db_session.commit()

    duplicate = SourceConnection(
        project_id=project_id,
        source_type="hubspot",
        access_token="access-2",
        refresh_token="refresh-2",
        instance_url="https://api.hubapi.com",
    )
    db_session.add(duplicate)
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_destination_connection_stores_metadata(db_session: AsyncSession) -> None:
    project_id = await _create_project(db_session)

    connection = DestinationConnection(
        project_id=project_id,
        destination_type="meta_capi",
        access_token="meta-access",
        refresh_token="meta-refresh",
        metadata_={"pixelId": "123456"},
    )
    db_session.add(connection)
    await db_session.commit()

    result = await db_session.execute(
        select(DestinationConnection).where(
            DestinationConnection.project_id == project_id,
            DestinationConnection.destination_type == "meta_capi",
        )
    )
    row = result.scalar_one()
    assert row.metadata_ == {"pixelId": "123456"}
