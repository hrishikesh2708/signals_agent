from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graph.handlers import (
    classify_scope,
    compose_scope_reply,
    format_channel_lines,
    format_signal_type_lines,
)
from app.graph.nodes import scope_guard_node
from app.graph.state import ScopePhase


@pytest.mark.asyncio
async def test_classify_scope_uses_single_human_message_only() -> None:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            content='{"status":"in_scope","reply_kind":"ack","matched_tokens":[]}'
        )
    )

    await classify_scope(llm, "connect Salesforce to Meta")

    llm.ainvoke.assert_awaited_once()
    messages = llm.ainvoke.await_args.args[0]
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "connect Salesforce to Meta"


@pytest.mark.asyncio
async def test_compose_scope_reply_uses_single_human_message_only() -> None:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Sure, I can help with that."))
    scope: ScopePhase = {
        "status": "in_scope",
        "reply_kind": "ack",
        "matched_tokens": [],
    }

    reply = await compose_scope_reply(llm, "hello setup", scope, "Ada")

    assert reply == "Sure, I can help with that."
    messages = llm.ainvoke.await_args.args[0]
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "hello setup"


@pytest.mark.asyncio
async def test_scope_guard_node_passes_last_human_only() -> None:
    classify = AsyncMock(
        return_value={
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                {
                    "raw": "Salesforce",
                    "id": "salesforce",
                    "display_name": "Salesforce",
                    "confidence": 0.5,
                }
            ],
        }
    )
    compose = AsyncMock(return_value="Happy to help with signal setup.")

    with (
        patch("app.graph.nodes.scope_guard.get_llm", return_value=MagicMock()),
        patch("app.graph.nodes.scope_guard.classify_scope", classify),
        patch("app.graph.nodes.scope_guard.compose_scope_reply", compose),
    ):
        result = await scope_guard_node(
            {
                "messages": [
                    AIMessage(content="welcome"),
                    HumanMessage(content="older turn"),
                    HumanMessage(content="connect Salesforce to Meta"),
                ],
                "user_name": "Ada",
                "scope": None,
                "intent": None,
            }
        )

    classify.assert_awaited_once()
    assert classify.await_args.args[1] == "connect Salesforce to Meta"
    compose.assert_awaited_once()
    assert compose.await_args.args[1] == "connect Salesforce to Meta"

    scope = result["scope"]
    assert scope["status"] == "in_scope"
    # confidence 0.5 < 0.7 → dropped
    assert scope["matched_tokens"] == []
    assert result["messages"][0].content == "Happy to help with signal setup."


def test_format_channel_lines_are_slim() -> None:
    lines = format_channel_lines()
    assert "product_group=meta" in lines
    assert "short_label=Meta" in lines
    assert "product_group=google" in lines
    assert "meta_capi" not in lines
    assert "google_offline_conversions" not in lines
    assert "group_default" not in lines


def test_format_signal_type_lines_active_only_slim() -> None:
    lines = format_signal_type_lines()
    assert '"offline_conversion"' in lines
    assert "Offline Conversion" in lines
    assert "aliases" not in lines
    assert "inactive" not in lines
    # inactive types omitted
    assert "web_conversion" not in lines
    assert "lead_conversion" not in lines
