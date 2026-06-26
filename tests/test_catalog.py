from app.graph.handlers import normalize_matched_tokens


def test_normalize_source_and_destination_aliases() -> None:
    tokens = normalize_matched_tokens(["Salesforce", "facebook", "offline"])
    assert "salesforce" in tokens
    assert "meta_capi" in tokens
    assert "offline_conversion" in tokens


def test_normalize_deduplicates() -> None:
    tokens = normalize_matched_tokens(["meta", "meta_capi", "facebook"])
    assert tokens.count("meta_capi") == 1
