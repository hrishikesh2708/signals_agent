from app.graph.validators import normalize_matched_tokens, validate_scope_json


def test_in_scope_with_valid_tokens() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": ["salesforce", "meta"],
        },
        "connect salesforce to meta",
    )
    assert scope["status"] == "in_scope"
    assert scope["reply_kind"] == "ack"
    assert scope["matched_tokens"] == ["salesforce"]
    assert "meta" in scope["mentioned_platforms"]


def test_in_scope_strips_ambiguous_google_connectors() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                "salesforce",
                "meta_capi",
                "google_offline_conversions",
                "google_customer_match",
            ],
        },
        "connect salesforce to meta and google",
    )
    assert scope["matched_tokens"] == ["salesforce"]
    assert set(scope["mentioned_platforms"]) == {"meta", "google"}


def test_in_scope_empty_tokens_downgrades_to_redirect() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [],
        }
    )
    assert scope["status"] == "out_of_scope"
    assert scope["reply_kind"] == "redirect"
    assert scope["matched_tokens"] == []
    assert scope["mentioned_platforms"] == []


def test_in_scope_unknown_tokens_downgrades_to_redirect() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": ["not_a_real_connector"],
        }
    )
    assert scope["status"] == "out_of_scope"
    assert scope["reply_kind"] == "redirect"


def test_out_of_scope_greeting_preserved() -> None:
    scope = validate_scope_json(
        {
            "status": "out_of_scope",
            "reply_kind": "greeting",
            "matched_tokens": [],
        }
    )
    assert scope["status"] == "out_of_scope"
    assert scope["reply_kind"] == "greeting"


def test_invalid_json_shape_falls_back() -> None:
    scope = validate_scope_json(None)
    assert scope == {
        "status": "out_of_scope",
        "reply_kind": "redirect",
        "matched_tokens": [],
        "mentioned_platforms": [],
    }


def test_signal_type_token_normalized() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": ["offline_conversion"],
        }
    )
    assert scope["matched_tokens"] == ["offline_conversion"]


def test_normalize_source_and_destination_aliases() -> None:
    tokens = normalize_matched_tokens(["Salesforce", "facebook", "offline"])
    assert "salesforce" in tokens
    assert "meta_capi" in tokens
    assert "offline_conversion" in tokens


def test_normalize_deduplicates() -> None:
    tokens = normalize_matched_tokens(["meta", "meta_capi", "facebook"])
    assert tokens.count("meta_capi") == 1
