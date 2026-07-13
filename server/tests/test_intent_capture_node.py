from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graph.handlers import extract_intent
from app.graph.nodes import intent_capture_node
from app.graph.state import IntentPhase


@pytest.mark.asyncio
async def test_extract_intent_uses_channel_catalog_not_destinations() -> None:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            content='{"source":"salesforce","signal_type":"offline_conversion","channels":["meta"]}'
        )
    )

    parsed = await extract_intent(
        llm,
        [AIMessage(content="ack"), HumanMessage(content="Send Salesforce offline conversions to Meta")],
        ["salesforce", "meta"],
    )

    assert parsed == {
        "source": "salesforce",
        "signal_type": "offline_conversion",
        "channels": ["meta"],
    }
    messages = llm.ainvoke.await_args.args[0]
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "Send Salesforce offline conversions to Meta"
    prompt = messages[0].content
    assert "product_group=meta" in prompt
    assert "product_group=google" in prompt
    assert "offline_conversion" in prompt
    assert "meta_capi" not in prompt
    assert "google_offline_conversions" not in prompt
    assert "destinations" not in prompt.lower() or "no destinations field" in prompt.lower()


@pytest.mark.asyncio
async def test_intent_capture_silent_handoff_no_messages() -> None:
    """Capture updates intent only — no ack / question AIMessage."""
    intent: IntentPhase = {
        "source": "salesforce",
        "platform_mentions": ["meta"],
        "channels": ["meta"],
        "destinations": [],
        "signal_type": "offline_conversion",
        "status": "partial",
        "open_question": None,
        "attempt": 1,
        "missing": [],
    }
    llm = MagicMock()

    with (
        patch("app.graph.nodes.intent_capture.get_llm", return_value=llm),
        patch(
            "app.graph.nodes.intent_capture.extract_intent",
            new_callable=AsyncMock,
            return_value={
                "source": "salesforce",
                "channels": ["meta"],
                "signal_type": "offline_conversion",
            },
        ),
        patch("app.graph.nodes.intent_capture.build_intent_from_extract", return_value=intent) as build,
    ):
        result = await intent_capture_node(
            {
                "messages": [HumanMessage(content="Send Salesforce offline conversions to Meta")],
                "user_name": "Ada",
                "scope": {
                    "status": "in_scope",
                    "reply_kind": "ack",
                    "matched_tokens": [
                        {
                            "raw": "Salesforce",
                            "id": "salesforce",
                            "display_name": "Salesforce",
                            "confidence": 0.95,
                        },
                        {
                            "raw": "Meta",
                            "id": "meta",
                            "display_name": "Meta",
                            "confidence": 0.9,
                        },
                    ],
                    "mentioned_platforms": ["meta"],
                },
                "intent": None,
            }
        )

    build.assert_called_once()
    assert result == {"intent": intent}
    assert "messages" not in result
    llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_intent_capture_partial_also_silent() -> None:
    intent: IntentPhase = {
        "source": None,
        "platform_mentions": ["meta"],
        "channels": ["meta"],
        "destinations": [],
        "signal_type": "offline_conversion",
        "status": "partial",
        "open_question": "source",
        "attempt": 1,
        "missing": ["source"],
    }

    with (
        patch("app.graph.nodes.intent_capture.get_llm", return_value=MagicMock()),
        patch(
            "app.graph.nodes.intent_capture.extract_intent",
            new_callable=AsyncMock,
            return_value={"source": None, "channels": ["meta"], "signal_type": "offline_conversion"},
        ),
        patch("app.graph.nodes.intent_capture.build_intent_from_extract", return_value=intent),
    ):
        result = await intent_capture_node(
            {
                "messages": [HumanMessage(content="send offline conversions to Meta")],
                "user_name": None,
                "scope": {
                    "status": "in_scope",
                    "reply_kind": "ack",
                    "matched_tokens": [],
                    "mentioned_platforms": ["meta"],
                },
                "intent": None,
            }
        )

    assert result == {"intent": intent}
    assert not any(isinstance(item, AIMessage) for item in result.get("messages", []))
