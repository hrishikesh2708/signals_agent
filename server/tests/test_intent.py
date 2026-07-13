from app.destinations import get_destination_registry
from app.graph.routers import route_after_intent_capture, route_after_intent_clarify
from app.graph.validators import (
    build_intent_from_extract,
    derive_destinations,
    resolve_product_groups,
    with_derived_destinations,
)


def test_resolve_google_default_to_offline() -> None:
    destination_registry = get_destination_registry()
    result = resolve_product_groups(
        destination_registry,
        ["google_offline_conversions", "google_customer_match"],
        "send to google ads",
        "offline_conversion",
    )
    assert result == ["google_offline_conversions"]


def test_resolve_google_customer_match_disambiguator() -> None:
    destination_registry = get_destination_registry()
    result = resolve_product_groups(
        destination_registry,
        ["google_offline_conversions", "google_customer_match"],
        "build a google customer match audience",
        None,
    )
    assert result == ["google_customer_match"]


def test_build_intent_human_fields_full_still_partial() -> None:
    """Capture never completes — destinations stay empty until clarify derives."""
    intent = build_intent_from_extract(
        {
            "source": "salesforce",
            "channels": ["meta"],
            "signal_type": "offline_conversion",
        },
        ["salesforce", "meta", "offline_conversion"],
        "Send Salesforce offline conversions to Meta",
    )
    assert intent["status"] == "partial"
    assert intent["source"] == "salesforce"
    assert intent["channels"] == ["meta"]
    assert intent["destinations"] == []
    assert intent["signal_type"] == "offline_conversion"
    assert intent["open_question"] is None
    assert "missing" not in intent
    assert "platform_mentions" not in intent


def test_build_intent_never_sets_destinations() -> None:
    intent = build_intent_from_extract(
        {
            "source": "salesforce",
            "channels": ["meta", "google"],
            "signal_type": "offline_conversion",
            "destinations": ["meta_capi"],
        },
        [],
        "Send Salesforce offline conversions to Meta and Google",
    )
    assert intent["destinations"] == []
    assert set(intent["channels"]) == {"meta", "google"}


def test_build_intent_normalizes_connector_ids_to_product_groups() -> None:
    intent = build_intent_from_extract(
        {
            "source": "salesforce",
            "channels": ["meta_capi", "google_offline_conversions"],
            "signal_type": "offline_conversion",
        },
        [],
        "Send Salesforce offline conversions to Meta and Google",
    )
    assert set(intent["channels"]) == {"meta", "google"}
    assert intent["destinations"] == []


def test_build_intent_partial_missing_source() -> None:
    intent = build_intent_from_extract(
        {"source": None, "channels": ["meta"], "signal_type": "offline_conversion"},
        [],
        "send offline conversions to Meta",
    )
    assert intent["status"] == "partial"
    assert intent["open_question"] == "source"
    assert intent["channels"] == ["meta"]
    assert "missing" not in intent


def test_build_intent_maps_customer_match_connector_to_google_group() -> None:
    intent = build_intent_from_extract(
        {
            "source": "hubspot",
            "channels": ["google_customer_match"],
            "signal_type": "offline_conversion",
        },
        [],
        "hubspot offline conversions to google customer match audience",
    )
    assert intent["channels"] == ["google"]
    assert intent["destinations"] == []


def test_build_intent_meta_google_waits_for_signal_type() -> None:
    intent = build_intent_from_extract(
        {"source": "salesforce", "channels": ["meta", "google"], "signal_type": None},
        ["salesforce", "meta", "google"],
        "connect salesforce to meta and google",
    )
    assert intent["source"] == "salesforce"
    assert set(intent["channels"]) == {"meta", "google"}
    assert intent["signal_type"] is None
    assert intent["status"] == "partial"
    assert intent["open_question"] == "signal_type"
    assert intent["destinations"] == []


def test_build_intent_infers_signal_type_from_text() -> None:
    intent = build_intent_from_extract(
        {"source": "salesforce", "channels": ["meta"], "signal_type": None},
        ["salesforce", "meta"],
        "send offline conversions to meta",
    )
    assert intent["signal_type"] == "offline_conversion"
    assert intent["open_question"] is None


def test_build_intent_google_audience_signal_type() -> None:
    intent = build_intent_from_extract(
        {"source": None, "channels": [], "signal_type": "offline_conversion"},
        [],
        "create a google audience",
    )
    assert intent["destinations"] == []
    assert "google_customer_match" not in intent["channels"]


def test_route_after_intent_capture_always_clarify() -> None:
    assert route_after_intent_capture({"intent": {"status": "partial", "open_question": None}}) == (
        "intent_clarify"
    )
    assert route_after_intent_capture({"intent": {"status": "partial", "open_question": "source"}}) == (
        "intent_clarify"
    )
    assert route_after_intent_capture({}) == "intent_clarify"


def test_derive_destinations_matches_product_group_and_signal_type() -> None:
    assert derive_destinations(["meta"], "offline_conversion") == ["meta_capi"]
    assert derive_destinations(["google"], "offline_conversion") == ["google_offline_conversions"]
    assert set(derive_destinations(["meta", "google"], "offline_conversion")) == {
        "meta_capi",
        "google_offline_conversions",
    }


def test_derive_destinations_empty_when_inputs_incomplete() -> None:
    assert derive_destinations([], "offline_conversion") == []
    assert derive_destinations(["meta"], None) == []
    assert derive_destinations(["meta"], "audience") == []  # meta_capi is offline only


def test_with_derived_destinations_marks_complete() -> None:
    intent = build_intent_from_extract(
        {
            "source": "salesforce",
            "channels": ["meta", "google"],
            "signal_type": "offline_conversion",
        },
        [],
        "Send Salesforce offline conversions to Meta and Google",
    )
    assert intent["status"] == "partial"
    assert intent["open_question"] is None

    completed = with_derived_destinations(intent)
    assert completed["status"] == "complete"
    assert completed["open_question"] is None
    assert completed["hitl_prompted"] is False
    assert set(completed["destinations"]) == {"meta_capi", "google_offline_conversions"}
    assert "missing" not in completed


def test_route_after_intent_clarify_ends_on_complete() -> None:
    assert (
        route_after_intent_clarify({"intent": {"status": "complete", "open_question": None}})
        == "__end__"
    )
    assert (
        route_after_intent_clarify(
            {"intent": {"status": "partial", "open_question": "source", "attempt": 1}}
        )
        == "intent_clarify"
    )
    # open_question None without complete should not loop (derive happens in-node)
    assert (
        route_after_intent_clarify(
            {"intent": {"status": "partial", "open_question": None, "attempt": 1}}
        )
        == "__end__"
    )
    assert (
        route_after_intent_clarify(
            {"intent": {"status": "partial", "open_question": "source", "attempt": 4}}
        )
        == "__end__"
    )
