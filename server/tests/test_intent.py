from app.destinations import get_destination_registry
from app.graph.routers import route_after_intent_capture, route_after_intent_clarify
from app.graph.validators import (
    build_clarify_payload,
    build_intent_from_extract,
    derive_destinations,
    infer_signal_type,
    merge_intent_selection,
    parse_clarify_selection,
    recompute_intent,
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
    assert "source" in intent["missing"]
    assert intent["channels"] == ["meta"]


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


def test_merge_intent_selection_fills_human_fields() -> None:
    current = recompute_intent(None, [], [], None, 1)
    merged = merge_intent_selection(
        {
            "source": "salesforce",
            "channels": ["meta"],
            "signal_type": "offline_conversion",
        },
        current,
        "Send Salesforce offline conversions to Meta",
    )
    assert merged["status"] == "partial"
    assert merged["open_question"] is None
    assert merged["channels"] == ["meta"]
    assert merged["destinations"] == []


def test_merge_normalizes_channel_selection_to_product_group() -> None:
    current = recompute_intent("salesforce", ["google"], [], "offline_conversion", 1)
    merged = merge_intent_selection(
        {
            "channels": ["google_customer_match", "meta_capi"],
        },
        current,
        "",
    )
    assert set(merged["channels"]) == {"google", "meta"}
    assert merged["open_question"] is None
    assert merged["destinations"] == []


def test_build_intent_meta_google_waits_for_signal_type() -> None:
    intent = build_intent_from_extract(
        {"source": "salesforce", "channels": ["meta", "google"], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    assert intent["source"] == "salesforce"
    assert set(intent["channels"]) == {"meta", "google"}
    assert intent["signal_type"] is None
    assert intent["status"] == "partial"
    assert intent["open_question"] == "signal_type"
    assert intent["destinations"] == []


def test_build_intent_resolves_channels_after_signal_type() -> None:
    current = build_intent_from_extract(
        {"source": "salesforce", "channels": ["meta", "google"], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    merged = merge_intent_selection(
        {"signal_type": "offline_conversion"},
        current,
        "connect salesforce to meta and google",
    )
    assert merged["open_question"] is None
    assert set(merged["channels"]) == {"meta", "google"}
    assert merged["destinations"] == []
    assert merged["status"] == "partial"


def test_infer_signal_type_requires_explicit_mention() -> None:
    assert infer_signal_type("connect salesforce to meta and google", []) is None
    assert infer_signal_type("send offline conversions to meta", []) == "offline_conversion"


def test_build_intent_google_audience_signal_type() -> None:
    intent = build_intent_from_extract(
        {"source": None, "channels": [], "signal_type": "offline_conversion"},
        [],
        "create a google audience",
    )
    assert intent["destinations"] == []
    assert "google_customer_match" not in intent["channels"]


def test_clarify_payload_single_field_for_source() -> None:
    intent = recompute_intent(None, [], [], None, 1)
    intent["open_question"] = "source"
    payload = build_clarify_payload(intent)
    assert payload["type"] == "intent_clarify"
    assert payload["open_question"] == "source"
    assert "field" in payload
    assert "fields" not in payload


def test_clarify_payload_signal_type_shows_platform_context() -> None:
    intent = build_intent_from_extract(
        {"source": "salesforce", "channels": ["meta", "google"], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    assert intent["open_question"] == "signal_type"
    payload = build_clarify_payload(intent)
    assert payload["open_question"] == "signal_type"
    assert set(payload["context"]["platform_mentions"]) == {"meta", "google"}
    assert set(payload["context"]["channels"]) == {"meta", "google"}
    assert payload["field"]["selected"] == "offline_conversion"


def test_clarify_payload_channels_uses_product_groups_multi() -> None:
    intent = recompute_intent("salesforce", [], [], "offline_conversion", 1)
    assert intent["open_question"] == "channels"
    payload = build_clarify_payload(intent)
    assert payload["open_question"] == "channels"
    assert payload["field"]["multi"] is True
    option_ids = {option["id"] for option in payload["field"]["options"]}
    assert option_ids == {"meta", "google"}


def test_parse_clarify_selection_accepts_studio_field_payload() -> None:
    parsed = parse_clarify_selection(
        {"field": {"selected": None, "suggested": "offline_conversion"}},
        "signal_type",
    )
    assert parsed == {"signal_type": "offline_conversion"}


def test_parse_clarify_selection_accepts_bare_string() -> None:
    parsed = parse_clarify_selection("offline_conversion", "signal_type")
    assert parsed == {"signal_type": "offline_conversion"}


def test_merge_from_studio_field_payload_completes_human_fields() -> None:
    current = build_intent_from_extract(
        {"source": "salesforce", "channels": ["meta", "google"], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    merged = merge_intent_selection(
        {"field": {"selected": None, "suggested": "offline_conversion"}},
        current,
        "connect salesforce to meta and google",
    )
    assert merged["open_question"] is None
    assert merged["signal_type"] == "offline_conversion"
    assert set(merged["channels"]) == {"meta", "google"}
    assert merged["destinations"] == []
    assert merged["status"] == "partial"


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
    assert set(completed["destinations"]) == {"meta_capi", "google_offline_conversions"}
    assert completed["missing"] == []


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