from app.graph.handlers import validate_scope_json


def test_in_scope_with_valid_tokens() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": ["salesforce", "meta"],
        }
    )
    assert scope["status"] == "in_scope"
    assert scope["reply_kind"] == "ack"
    assert "salesforce" in scope["matched_tokens"]
    assert "meta_capi" in scope["matched_tokens"]


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
