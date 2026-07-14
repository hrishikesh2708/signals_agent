import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from app.graph.handlers import format_intent_clarify_ack, format_intent_summary_message
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


def _awaiting_signal_type() -> IntentPhase:
    return {
        "source": "salesforce",
        "channels": ["meta"],
        "destinations": [],
        "signal_type": None,
        "status": "partial",
        "open_question": "signal_type",
        "attempt": 1,
        "hitl_prompted": True,
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


@pytest.mark.asyncio
async def test_intent_clarify_resume_emits_step_complete_then_summary() -> None:
    """HITL signal_type resume with other fields filled → step_complete + intent_summary."""
    intent = _awaiting_signal_type()
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Setup confirmed."))

    with (
        patch("app.graph.nodes.intent_clarify.get_llm", return_value=llm),
        patch(
            "app.graph.nodes.intent_clarify.interrupt",
            return_value={"selected": "offline_conversion"},
        ),
    ):
        result = await intent_clarify_node(
            {
                "messages": [HumanMessage(content="map sf to meta")],
                "user_name": "Ada",
                "scope": None,
                "intent": intent,
            }
        )

    assert result["intent"]["status"] == "complete"
    assert len(result["messages"]) == 2
    ack = json.loads(result["messages"][0].content)
    assert ack["type"] == "step_complete"
    assert ack["message"] == "Offline Conversion selected as signal type"
    summary = json.loads(result["messages"][1].content)
    assert summary["type"] == "intent_summary"


@pytest.mark.asyncio
async def test_intent_clarify_resume_emits_step_complete_when_more_fields() -> None:
    """HITL signal_type resume with channels still open → step_complete only."""
    intent: IntentPhase = {
        "source": "salesforce",
        "channels": [],
        "destinations": [],
        "signal_type": None,
        "status": "partial",
        "open_question": "signal_type",
        "attempt": 1,
        "hitl_prompted": True,
    }

    with (
        patch("app.graph.nodes.intent_clarify.get_llm"),
        patch(
            "app.graph.nodes.intent_clarify.interrupt",
            return_value={"selected": "offline_conversion"},
        ),
    ):
        result = await intent_clarify_node(
            {
                "messages": [HumanMessage(content="map sf")],
                "user_name": "Ada",
                "scope": None,
                "intent": intent,
            }
        )

    assert result["intent"]["open_question"] == "channels"
    assert result["intent"]["signal_type"] == "offline_conversion"
    assert len(result["messages"]) == 1
    ack = json.loads(result["messages"][0].content)
    assert ack["type"] == "step_complete"
    assert ack["message"] == "Offline Conversion selected as signal type"


def test_format_intent_summary_message_shape() -> None:
    intent = with_derived_destinations(_full_human_intent())
    raw = format_intent_summary_message(intent, "Setup confirmed.")
    payload = json.loads(raw)
    assert payload["type"] == "intent_summary"
    assert payload["message"] == "Setup confirmed."
    assert payload["details"]["source_label"] == "Salesforce"
    assert payload["details"]["destinations"] == ["meta_capi"]
    assert payload["details"]["destination_labels"]


def test_format_intent_clarify_ack_messages() -> None:
    source_ack = json.loads(
        format_intent_clarify_ack(
            "source",
            {**_full_human_intent(), "open_question": None},
        )
        or ""
    )
    assert source_ack["message"] == "Salesforce selected as data source"

    signal_ack = json.loads(
        format_intent_clarify_ack(
            "signal_type",
            {**_full_human_intent(), "open_question": None},
        )
        or ""
    )
    assert signal_ack["message"] == "Offline Conversion selected as signal type"

    channels_ack = json.loads(
        format_intent_clarify_ack(
            "channels",
            {
                **_full_human_intent(),
                "channels": ["meta", "google"],
                "open_question": None,
            },
        )
        or ""
    )
    assert channels_ack["message"] == "Meta + Google selected as destinations"