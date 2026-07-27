from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage

from app.graph.nodes.source_connection import source_connection_node


@pytest.mark.asyncio
async def test_source_connection_already_connected_writes_source_phase() -> None:
    project_id = str(uuid4())
    with (
        patch(
            "app.graph.nodes.source_connection.resolve_source",
            return_value="salesforce",
        ),
        patch(
            "app.graph.nodes.source_connection.is_supported_source",
            return_value=True,
        ),
        patch(
            "app.graph.nodes.source_connection.get_source",
            return_value=MagicMock(display_name="Salesforce"),
        ),
        patch(
            "app.graph.nodes.source_connection._connection_status",
            new=AsyncMock(return_value=(True, "Acme Prod")),
        ),
        patch("app.graph.nodes.source_connection.interrupt") as mock_interrupt,
    ):
        result = await source_connection_node(
            {
                "messages": [HumanMessage(content="map sf")],
                "user_name": "Ada",
                "project_id": project_id,
                "intent": {
                    "source": "salesforce",
                    "channels": ["meta"],
                    "destinations": ["meta_capi"],
                    "signal_type": "offline_conversion",
                    "status": "complete",
                    "open_question": None,
                    "attempt": 1,
                    "hitl_prompted": False,
                },
                "scope": None,
            }
        )

    mock_interrupt.assert_not_called()
    source = result["source"]
    assert source["source_id"] == "salesforce"
    assert source["source_label"] == "Salesforce"
    assert source["project_name"] == "Acme Prod"
    assert source["status"] == "connected"
    assert source["object_name"] is None
    assert source["recommended_object"] is None
    assert source["object_hitl_prompted"] is False
    assert "Salesforce connected" in result["messages"][0].content
