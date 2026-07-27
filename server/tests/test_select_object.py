import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from app.graph.handlers.select_object import compose_object_suggestion
from app.graph.nodes.select_object import select_object_node
from app.graph.routers import route_after_select_object, route_after_source_connection
from app.graph.state import SourcePhase
from app.graph.validators.select_object import (
    build_select_object_payload,
    format_select_object_ack,
    format_select_object_ask,
    parse_select_object_resume,
    validate_recommended,
)


OPTIONS = ["Lead", "Contact", "Account", "Opportunity"]


def _connected_source(**overrides: object) -> SourcePhase:
    base: SourcePhase = {
        "source_id": "salesforce",
        "source_label": "Salesforce",
        "project_name": "Acme Prod",
        "status": "connected",
        "object_name": None,
        "recommended_object": None,
        "object_hitl_prompted": False,
    }
    return {**base, **overrides}  # type: ignore[return-value]


def test_validate_recommended_exact_membership() -> None:
    assert validate_recommended("Opportunity", OPTIONS) == "Opportunity"
    assert validate_recommended("opportunity", OPTIONS) is None
    assert validate_recommended("Campaign", OPTIONS) is None
    assert validate_recommended(None, OPTIONS) is None
    assert validate_recommended("", OPTIONS) is None


def test_build_select_object_payload_with_and_without_recommended() -> None:
    with_rec = build_select_object_payload(
        options=OPTIONS,
        recommended="Opportunity",
        source_id="salesforce",
    )
    assert with_rec["type"] == "select_object"
    assert with_rec["title"] == "Select object"
    assert with_rec["options"] == OPTIONS
    assert with_rec["recommended"] == "Opportunity"
    assert with_rec["default_selected"] == "Opportunity"

    without = build_select_object_payload(
        options=OPTIONS,
        recommended=None,
        source_id="salesforce",
    )
    assert "recommended" not in without
    assert "default_selected" not in without


def test_parse_select_object_resume() -> None:
    assert parse_select_object_resume({"selected": "Opportunity"}, OPTIONS) == "Opportunity"
    assert parse_select_object_resume({"selected": "Campaign"}, OPTIONS) is None
    assert parse_select_object_resume({"selected": ["Opportunity"]}, OPTIONS) is None
    assert parse_select_object_resume("Opportunity", OPTIONS) is None


def test_format_select_object_ack_and_ask() -> None:
    ask = format_select_object_ask(source_label="Salesforce", project_name="Acme Prod")
    assert "Salesforce is connected as Acme Prod" in ask
    assert "Which object holds the conversions" in ask

    ack = json.loads(format_select_object_ack("Opportunity"))
    assert ack == {
        "type": "step_complete",
        "message": "Opportunity selected as source object",
    }


@pytest.mark.asyncio
async def test_compose_object_suggestion_rejects_invalid_pick() -> None:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            content=json.dumps(
                {
                    "recommended": "Campaign",
                    "rationale": "Campaigns hold conversions.",
                }
            )
        )
    )
    recommended, rationale = await compose_object_suggestion(
        llm,
        source_label="Salesforce",
        signal_type="offline_conversion",
        project_name="Acme Prod",
        options=OPTIONS,
    )
    assert recommended is None
    assert rationale is None


@pytest.mark.asyncio
async def test_compose_object_suggestion_accepts_valid_pick() -> None:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            content=json.dumps(
                {
                    "recommended": "Opportunity",
                    "rationale": (
                        "For offline sales conversions, Opportunities usually holds "
                        "the closed-deal value and date. Confirm or pick another."
                    ),
                }
            )
        )
    )
    recommended, rationale = await compose_object_suggestion(
        llm,
        source_label="Salesforce",
        signal_type="offline_conversion",
        project_name="Acme Prod",
        options=OPTIONS,
    )
    assert recommended == "Opportunity"
    assert rationale is not None
    assert "Opportunities" in rationale


@pytest.mark.asyncio
async def test_select_object_visit_a_emits_ask_and_optional_rationale() -> None:
    source = _connected_source()
    with (
        patch("app.graph.nodes.select_object.get_llm", return_value=MagicMock()),
        patch(
            "app.graph.nodes.select_object.compose_object_suggestion",
            new=AsyncMock(
                return_value=(
                    "Opportunity",
                    "For offline sales conversions, Opportunities usually holds the closed-deal value and date. Confirm or pick another.",
                )
            ),
        ),
        patch("app.graph.nodes.select_object.interrupt") as mock_interrupt,
        patch(
            "app.graph.nodes.select_object.get_source",
            return_value=MagicMock(objects_common=tuple(OPTIONS)),
        ),
    ):
        result = await select_object_node(
            {
                "messages": [HumanMessage(content="map sf")],
                "user_name": "Ada",
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
                "source": source,
                "scope": None,
            }
        )

    mock_interrupt.assert_not_called()
    assert result["source"]["object_hitl_prompted"] is True
    assert result["source"]["recommended_object"] == "Opportunity"
    assert result["source"]["object_name"] is None
    assert len(result["messages"]) == 1
    content = result["messages"][0].content
    assert "Salesforce is connected as Acme Prod" in content
    assert "Opportunities usually holds" in content


@pytest.mark.asyncio
async def test_select_object_visit_a_without_recommendation() -> None:
    source = _connected_source()
    with (
        patch("app.graph.nodes.select_object.get_llm", return_value=MagicMock()),
        patch(
            "app.graph.nodes.select_object.compose_object_suggestion",
            new=AsyncMock(return_value=(None, None)),
        ),
        patch(
            "app.graph.nodes.select_object.get_source",
            return_value=MagicMock(objects_common=tuple(OPTIONS)),
        ),
    ):
        result = await select_object_node(
            {
                "messages": [HumanMessage(content="map sf")],
                "user_name": "Ada",
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
                "source": source,
                "scope": None,
            }
        )

    assert result["source"]["recommended_object"] is None
    assert result["source"]["object_hitl_prompted"] is True
    assert len(result["messages"]) == 1


@pytest.mark.asyncio
async def test_select_object_visit_b_sets_object_name() -> None:
    source = _connected_source(
        object_hitl_prompted=True,
        recommended_object="Opportunity",
    )
    with (
        patch(
            "app.graph.nodes.select_object.interrupt",
            return_value={"selected": "Lead"},
        ),
        patch(
            "app.graph.nodes.select_object.get_source",
            return_value=MagicMock(objects_common=tuple(OPTIONS)),
        ),
        patch(
            "app.graph.nodes.select_object.object_exists_via_describe",
            new=AsyncMock(return_value=True),
        ) as mock_describe,
    ):
        result = await select_object_node(
            {
                "messages": [HumanMessage(content="map sf")],
                "user_name": "Ada",
                "project_id": "11111111-1111-1111-1111-111111111111",
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
                "source": source,
                "scope": None,
            }
        )

    mock_describe.assert_awaited_once()
    assert result["source"]["object_name"] == "Lead"
    assert result["source"]["object_hitl_prompted"] is False
    ack = json.loads(result["messages"][0].content)
    assert ack["type"] == "step_complete"
    assert "Lead selected as source object" in ack["message"]


@pytest.mark.asyncio
async def test_select_object_visit_b_describe_failure_keeps_hitl() -> None:
    source = _connected_source(
        object_hitl_prompted=True,
        recommended_object="Opportunity",
    )
    with (
        patch(
            "app.graph.nodes.select_object.interrupt",
            return_value={"selected": "Lead"},
        ),
        patch(
            "app.graph.nodes.select_object.get_source",
            return_value=MagicMock(objects_common=tuple(OPTIONS)),
        ),
        patch(
            "app.graph.nodes.select_object.object_exists_via_describe",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await select_object_node(
            {
                "messages": [HumanMessage(content="map sf")],
                "user_name": "Ada",
                "project_id": "11111111-1111-1111-1111-111111111111",
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
                "source": source,
                "scope": None,
            }
        )

    assert "source" not in result
    assert "couldn't confirm Lead" in result["messages"][0].content


@pytest.mark.asyncio
async def test_select_object_visit_b_yaml_reject_skips_describe() -> None:
    source = _connected_source(object_hitl_prompted=True)
    with (
        patch(
            "app.graph.nodes.select_object.interrupt",
            return_value={"selected": "Campaign"},
        ),
        patch(
            "app.graph.nodes.select_object.get_source",
            return_value=MagicMock(objects_common=tuple(OPTIONS)),
        ),
        patch(
            "app.graph.nodes.select_object.object_exists_via_describe",
            new=AsyncMock(return_value=True),
        ) as mock_describe,
    ):
        result = await select_object_node(
            {
                "messages": [HumanMessage(content="map sf")],
                "user_name": "Ada",
                "project_id": "11111111-1111-1111-1111-111111111111",
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
                "source": source,
                "scope": None,
            }
        )

    mock_describe.assert_not_called()
    assert "source" not in result
    assert "isn't available" in result["messages"][0].content


def test_route_after_source_connection() -> None:
    assert (
        route_after_source_connection({"source": {"status": "connected"}})
        == "select_object"
    )
    assert route_after_source_connection({}) == "__end__"
    assert route_after_source_connection({"source": {}}) == "__end__"


def test_route_after_select_object() -> None:
    assert (
        route_after_select_object(
            {"source": {"status": "connected", "object_name": "Opportunity"}}
        )
        == "__end__"
    )
    assert (
        route_after_select_object(
            {
                "source": {
                    "status": "connected",
                    "object_name": None,
                    "object_hitl_prompted": True,
                }
            }
        )
        == "select_object"
    )
    assert route_after_select_object({}) == "__end__"
