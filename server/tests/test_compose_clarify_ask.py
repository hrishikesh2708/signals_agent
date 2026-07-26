from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.graph.handlers.intent import (
    _usable_clarify_ask,
    compose_intent_clarify_message,
)
from app.graph.state import IntentPhase


def test_usable_clarify_ask_rejects_field_ids() -> None:
    assert _usable_clarify_ask("signal_type", "signal_type") is False
    assert _usable_clarify_ask("channels", "channels") is False
    assert _usable_clarify_ask("source", "source") is False
    assert _usable_clarify_ask("  signal_type. ", "signal_type") is False
    assert _usable_clarify_ask("ok", "signal_type") is False  # too short


def test_usable_clarify_ask_accepts_natural_language() -> None:
    assert (
        _usable_clarify_ask(
            "Before we pick destinations, please confirm the signal type.",
            "signal_type",
        )
        is True
    )


@pytest.mark.asyncio
async def test_compose_falls_back_when_llm_returns_field_id() -> None:
    intent: IntentPhase = {
        "source": "salesforce",
        "channels": [],
        "destinations": [],
        "signal_type": None,
        "status": "partial",
        "open_question": "signal_type",
        "attempt": 1,
        "hitl_prompted": False,
    }
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="signal_type"))

    text = await compose_intent_clarify_message(llm, [HumanMessage(content="hi")], intent, [])

    assert text != "signal_type"
    assert "signal type" in text.lower() or "offline" in text.lower()
    assert llm.ainvoke.await_args.kwargs.get("config", {}).get("metadata", {}).get(
        "emit-messages"
    ) is False
