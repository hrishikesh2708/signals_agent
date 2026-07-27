from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.source_describe import object_exists_via_describe
from app.sources import SourceAuthError


@pytest.mark.asyncio
async def test_object_exists_via_describe_success() -> None:
    project_id = uuid4()
    connection = MagicMock(
        instance_url="https://example.my.salesforce.com",
        access_token="tok",
        refresh_token="ref",
    )
    registry = MagicMock()
    registry.describe_object = AsyncMock(return_value=[])

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=connection))
    )

    with (
        patch("app.services.source_describe.async_session_factory", return_value=db),
        patch(
            "app.services.source_describe.get_source_registry",
            return_value=registry,
        ),
    ):
        ok = await object_exists_via_describe(project_id, "salesforce", "Opportunity")

    assert ok is True
    registry.describe_object.assert_awaited_once()


@pytest.mark.asyncio
async def test_object_exists_via_describe_no_connection() -> None:
    project_id = uuid4()
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    with patch("app.services.source_describe.async_session_factory", return_value=db):
        ok = await object_exists_via_describe(project_id, "salesforce", "Opportunity")

    assert ok is False


@pytest.mark.asyncio
async def test_object_exists_via_describe_failure() -> None:
    project_id = uuid4()
    connection = MagicMock(
        instance_url="https://example.my.salesforce.com",
        access_token="tok",
        refresh_token="ref",
    )
    registry = MagicMock()
    registry.describe_object = AsyncMock(side_effect=RuntimeError("not found"))

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=connection))
    )

    with (
        patch("app.services.source_describe.async_session_factory", return_value=db),
        patch(
            "app.services.source_describe.get_source_registry",
            return_value=registry,
        ),
    ):
        ok = await object_exists_via_describe(project_id, "salesforce", "Opportunity")

    assert ok is False


@pytest.mark.asyncio
async def test_object_exists_via_describe_refresh_retry() -> None:
    project_id = uuid4()
    connection = MagicMock(
        instance_url="https://example.my.salesforce.com",
        access_token="old",
        refresh_token="ref",
    )
    registry = MagicMock()
    registry.describe_object = AsyncMock(
        side_effect=[SourceAuthError("expired"), []]
    )
    connector = MagicMock()
    connector.refresh = AsyncMock(return_value={"access_token": "new"})

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=connection))
    )
    db.commit = AsyncMock()

    with (
        patch("app.services.source_describe.async_session_factory", return_value=db),
        patch(
            "app.services.source_describe.get_source_registry",
            return_value=registry,
        ),
        patch(
            "app.services.source_describe.get_connector",
            return_value=connector,
        ),
    ):
        ok = await object_exists_via_describe(project_id, "salesforce", "Opportunity")

    assert ok is True
    assert connection.access_token == "new"
    assert registry.describe_object.await_count == 2
    db.commit.assert_awaited_once()
