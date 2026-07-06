from app.destinations import get_destination_registry
from app.graph.validators import (
    build_clarify_payload,
    build_intent_from_extract,
    infer_signal_type,
    mention_destinations,
    merge_intent_selection,
    parse_clarify_selection,
    recompute_intent,
    resolve_product_groups,
    sanitize_scope_hints,
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


def test_mention_destinations_bare_google() -> None:
    result = mention_destinations("send conversions to google ads", "offline_conversion")
    assert result == ["google_offline_conversions"]


def test_sanitize_scope_moves_connectors_to_platforms() -> None:
    matched, platforms = sanitize_scope_hints(
        ["salesforce", "meta_capi", "google_offline_conversions", "google_customer_match"],
        "connect salesforce to meta and google",
    )
    assert matched == ["salesforce"]
    assert set(platforms) == {"meta", "google"}


def test_build_intent_complete_from_text() -> None:
    intent = build_intent_from_extract(
        {
            "source": "salesforce",
            "channels": ["meta_capi"],
            "signal_type": "offline_conversion",
        },
        ["salesforce", "meta_capi", "offline_conversion"],
        "Send Salesforce offline conversions to Meta",
    )
    assert intent["status"] == "complete"
    assert intent["source"] == "salesforce"
    assert intent["channels"] == ["meta_capi"]
    assert intent["signal_type"] == "offline_conversion"
    assert intent["open_question"] is None


def test_build_intent_partial_missing_source() -> None:
    intent = build_intent_from_extract(
        {"source": None, "channels": ["meta_capi"], "signal_type": "offline_conversion"},
        [],
        "send offline conversions to Meta",
    )
    assert intent["status"] == "partial"
    assert intent["open_question"] == "source"
    assert "source" in intent["missing"]


def test_build_intent_strips_customer_match_for_offline_v1() -> None:
    intent = build_intent_from_extract(
        {"source": "hubspot", "channels": ["google_customer_match"], "signal_type": "offline_conversion"},
        [],
        "hubspot offline conversions to google customer match audience",
    )
    assert "google_customer_match" not in intent["channels"]


def test_merge_intent_selection_complete() -> None:
    current = recompute_intent(None, [], [], None, 1)
    merged = merge_intent_selection(
        {
            "source": "salesforce",
            "channels": ["meta_capi"],
            "signal_type": "offline_conversion",
        },
        current,
        "Send Salesforce offline conversions to Meta",
    )
    assert merged["status"] == "complete"
    assert merged["open_question"] is None


def test_merge_rejects_customer_match_selection() -> None:
    current = recompute_intent("salesforce", ["google"], [], None, 1)
    merged = merge_intent_selection(
        {
            "source": "salesforce",
            "channels": ["google_customer_match"],
            "signal_type": "offline_conversion",
        },
        current,
        "",
    )
    assert "google_customer_match" not in merged["channels"]
    assert merged["channels"] == ["google_offline_conversions"]
    assert merged["status"] == "complete"


def test_mention_meta_and_google_offline() -> None:
    result = mention_destinations("send offline conversions to meta and google", "offline_conversion")
    assert set(result) == {"meta_capi", "google_offline_conversions"}


def test_mention_youtube_defaults_to_google_offline() -> None:
    result = mention_destinations("send to youtube", None)
    assert result == ["google_offline_conversions"]


def test_build_intent_meta_google_waits_for_signal_type() -> None:
    intent = build_intent_from_extract(
        {"source": "salesforce", "channels": ["meta_capi", "google_offline_conversions"], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    assert intent["source"] == "salesforce"
    assert intent["channels"] == []
    assert set(intent["platform_mentions"]) == {"meta", "google"}
    assert intent["signal_type"] is None
    assert intent["status"] == "partial"
    assert intent["open_question"] == "signal_type"


def test_build_intent_resolves_connectors_after_signal_type() -> None:
    current = build_intent_from_extract(
        {"source": "salesforce", "channels": [], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    merged = merge_intent_selection(
        {"signal_type": "offline_conversion"},
        current,
        "connect salesforce to meta and google",
    )
    assert merged["status"] == "complete"
    assert set(merged["channels"]) == {"meta_capi", "google_offline_conversions"}


def test_infer_signal_type_requires_explicit_mention() -> None:
    assert infer_signal_type("connect salesforce to meta and google", []) is None
    assert infer_signal_type("send offline conversions to meta", []) == "offline_conversion"


def test_build_intent_google_audience_signal_type() -> None:
    intent = build_intent_from_extract(
        {"source": None, "channels": [], "signal_type": "offline_conversion"},
        [],
        "create a google audience",
    )
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
        {"source": "salesforce", "channels": [], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    assert intent["open_question"] == "signal_type"
    payload = build_clarify_payload(intent)
    assert payload["open_question"] == "signal_type"
    assert payload["context"]["platform_mentions"] == ["meta", "google"]
    assert payload["context"]["channels"] == []
    assert payload["field"]["selected"] == "offline_conversion"


def test_parse_clarify_selection_accepts_studio_field_payload() -> None:
    parsed = parse_clarify_selection(
        {"field": {"selected": None, "suggested": "offline_conversion"}},
        "signal_type",
    )
    assert parsed == {"signal_type": "offline_conversion"}


def test_parse_clarify_selection_accepts_bare_string() -> None:
    parsed = parse_clarify_selection("offline_conversion", "signal_type")
    assert parsed == {"signal_type": "offline_conversion"}


def test_merge_from_studio_field_payload_completes() -> None:
    current = build_intent_from_extract(
        {"source": "salesforce", "channels": [], "signal_type": None},
        ["salesforce"],
        "connect salesforce to meta and google",
        ["meta", "google"],
    )
    merged = merge_intent_selection(
        {"field": {"selected": None, "suggested": "offline_conversion"}},
        current,
        "connect salesforce to meta and google",
    )
    assert merged["status"] == "complete"
    assert merged["signal_type"] == "offline_conversion"
    assert set(merged["channels"]) == {"meta_capi", "google_offline_conversions"}
