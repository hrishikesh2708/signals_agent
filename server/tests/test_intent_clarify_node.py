import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from app.graph.handlers import format_intent_summary_message
from app.graph.nodes import intent_clarify_node
from app.graph.state import IntentPhase
from app.graph.validators import with_derived_destinations


def _full_human_intent() -> IntentPhase:
    return {
        "source": "salesforce",
        "channels": ["meta"],
        "destinations": [],
        "signal_type": "offline_conversion",
        "status": "partial",
        "open_question": None,
        "attempt": 1,
        "hitl_prompted": False,
    }


@pytest.mark.asyncio
async def test_intent_clarify_skips_hitl_when_human_fields_full() -> None:
    """Full human fields → derive destinations + intent_summary; no interrupt."""
    intent = _full_human_intent()
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Confirmed Salesforce → Meta setup."))

    with (
        patch("app.graph.nodes.intent_clarify.get_llm", return_value=llm),
        patch("app.graph.nodes.intent_clarify.interrupt") as mock_interrupt,
    ):
        result = await intent_clarify_node(
            {
                "messages": [HumanMessage(content="Send Salesforce offline conversions to Meta")],
                "user_name": "Ada",
                "scope": {
                    "status": "in_scope",
                    "reply_kind": "ack",
                    "matched_tokens": [],
                },
                "intent": intent,
            }
        )

    mock_interrupt.assert_not_called()
    completed = result["intent"]
    assert completed["status"] == "complete"
    assert completed["destinations"] == ["meta_capi"]
    assert completed["open_question"] is None

    assert len(result["messages"]) == 1
    content = result["messages"][0].content
    assert isinstance(content, str)
    payload = json.loads(content)
    assert payload["type"] == "intent_summary"
    assert "message" in payload
    assert payload["details"]["source"] == "salesforce"
    assert payload["details"]["destinations"] == ["meta_capi"]


def test_format_intent_summary_message_shape() -> None:
    intent = with_derived_destinations(_full_human_intent())
    raw = format_intent_summary_message(intent, "Setup confirmed.")
    payload = json.loads(raw)
    assert payload["type"] == "intent_summary"
    assert payload["message"] == "Setup confirmed."
    assert payload["details"]["source_label"] == "Salesforce"
    assert payload["details"]["destinations"] == ["meta_capi"]
    assert payload["details"]["destination_labels"]
