from app.graph.validators import normalize_matched_tokens, validate_scope_json


def _token(
    *,
    raw: str,
    token_id: str,
    display_name: str,
    confidence: float,
) -> dict:
    return {
        "raw": raw,
        "id": token_id,
        "display_name": display_name,
        "confidence": confidence,
    }


def test_in_scope_with_valid_tokens() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                _token(
                    raw="Salesforce",
                    token_id="salesforce",
                    display_name="Salesforce",
                    confidence=0.92,
                ),
                _token(
                    raw="Meta",
                    token_id="meta",
                    display_name="Meta",
                    confidence=0.9,
                ),
            ],
        },
        "connect salesforce to meta",
    )
    assert scope["status"] == "in_scope"
    assert scope["reply_kind"] == "ack"
    assert len(scope["matched_tokens"]) == 2
    assert scope["matched_tokens"][0]["id"] == "salesforce"
    assert scope["matched_tokens"][1]["id"] == "meta"
    assert scope["mentioned_platforms"] == ["meta"]


def test_channels_connector_id_mapped_to_product_group() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                _token(
                    raw="Salesforce",
                    token_id="salesforce",
                    display_name="Salesforce",
                    confidence=0.95,
                ),
                _token(
                    raw="Meta CAPI",
                    token_id="meta_capi",
                    display_name="Meta",
                    confidence=0.9,
                ),
                _token(
                    raw="Google Ads",
                    token_id="google_offline_conversions",
                    display_name="Google",
                    confidence=0.88,
                ),
            ],
        },
        "connect salesforce to meta and google",
    )
    ids = {token["id"] for token in scope["matched_tokens"]}
    assert "salesforce" in ids
    assert "meta" in ids
    assert "google" in ids
    assert "meta_capi" not in ids
    assert "google_offline_conversions" not in ids
    assert set(scope["mentioned_platforms"]) == {"meta", "google"}


def test_in_scope_empty_tokens_preserves_in_scope() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [],
        }
    )
    assert scope["status"] == "in_scope"
    assert scope["reply_kind"] == "ack"
    assert scope["matched_tokens"] == []
    assert scope["mentioned_platforms"] == []


def test_low_confidence_tokens_dropped() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                _token(
                    raw="maybe Salesforce",
                    token_id="salesforce",
                    display_name="Salesforce",
                    confidence=0.5,
                ),
                _token(
                    raw="Meta",
                    token_id="meta",
                    display_name="Meta",
                    confidence=0.7,
                ),
            ],
        }
    )
    assert len(scope["matched_tokens"]) == 1
    assert scope["matched_tokens"][0]["id"] == "meta"
    assert scope["mentioned_platforms"] == ["meta"]


def test_unknown_id_dropped() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                _token(
                    raw="foo",
                    token_id="not_a_real_connector",
                    display_name="Foo",
                    confidence=0.99,
                ),
            ],
        }
    )
    assert scope["status"] == "in_scope"
    assert scope["matched_tokens"] == []
    assert scope["mentioned_platforms"] == []


def test_unknown_channel_id_dropped() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                _token(
                    raw="unknown channel",
                    token_id="tiktok",
                    display_name="TikTok",
                    confidence=0.95,
                ),
            ],
        }
    )
    assert scope["matched_tokens"] == []
    assert scope["mentioned_platforms"] == []


def test_display_name_corrected_from_registry() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                _token(
                    raw="SF",
                    token_id="salesforce",
                    display_name="Wrong Label",
                    confidence=0.9,
                ),
            ],
        }
    )
    assert scope["matched_tokens"][0]["display_name"] == "Salesforce"
    assert scope["matched_tokens"][0]["raw"] == "SF"


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


def test_signal_type_token_kept() -> None:
    scope = validate_scope_json(
        {
            "status": "in_scope",
            "reply_kind": "ack",
            "matched_tokens": [
                _token(
                    raw="offline conversions",
                    token_id="offline_conversion",
                    display_name="Offline Conversion",
                    confidence=0.91,
                ),
            ],
        }
    )
    assert len(scope["matched_tokens"]) == 1
    assert scope["matched_tokens"][0]["id"] == "offline_conversion"
    assert scope["matched_tokens"][0]["display_name"] == "Offline Conversion"


def test_normalize_source_and_destination_aliases() -> None:
    tokens = normalize_matched_tokens(["Salesforce", "facebook", "offline"])
    assert "salesforce" in tokens
    assert "meta_capi" in tokens
    assert "offline_conversion" in tokens


def test_normalize_deduplicates() -> None:
    tokens = normalize_matched_tokens(["meta", "meta_capi", "facebook"])
    assert tokens.count("meta_capi") == 1
