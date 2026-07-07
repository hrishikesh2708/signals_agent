from app.destinations import (
    get_destination,
    get_destination_ids,
    get_destination_registry,
    get_routing_meta,
    is_supported_destination,
    list_destinations,
    resolve_destination,
)


def test_loads_three_destinations_from_yaml() -> None:
    catalog = get_destination_registry().destinations
    ids = {entry.id for entry in catalog}
    assert ids == {"meta_capi", "google_offline_conversions", "google_customer_match"}


def test_get_destinations_returns_catalog_entries() -> None:
    destinations = list_destinations()
    assert len(destinations) == 3
    assert all(entry.id for entry in destinations)
    offline = next(entry for entry in destinations if entry.id == "google_offline_conversions")
    assert offline.group_default is True


def test_resolve_destination_by_alias() -> None:
    assert resolve_destination("meta") == "meta_capi"
    assert resolve_destination("Meta Conversions API") == "meta_capi"
    assert resolve_destination("google_offline_conversions") == "google_offline_conversions"


def test_is_supported_destination() -> None:
    assert is_supported_destination("meta_capi") is True
    assert is_supported_destination("unknown") is False


def test_google_offline_is_group_default() -> None:
    meta = get_routing_meta()
    assert meta["google_offline_conversions"]["group_default"] is True
    assert meta["google_offline_conversions"]["product_group"] == "google"
    assert (
        meta["google_offline_conversions"]["oauth_path"]
        == "/api/auth/google?dest=google_offline_conversions"
    )
    assert meta["google_offline_conversions"]["event_destination"] is True


def test_google_offline_disambiguators_and_metadata() -> None:
    entry = get_destination("google_offline_conversions")
    assert entry is not None
    assert "gclid" in entry.disambiguators
    assert entry.signal_types == ("offline_conversion",)
    assert entry.required_metadata == ()
    assert entry.oauth.start_path == entry.oauth_path


def test_google_customer_match_disambiguators() -> None:
    meta = get_routing_meta()
    assert "customer match" in meta["google_customer_match"]["disambiguators"]
    assert meta["google_customer_match"]["signal_types"] == ["audience"]
    assert meta["google_customer_match"]["oauth_path"] == "/api/auth/google"


def test_meta_capi_fields_and_catalog() -> None:
    entry = get_destination("meta_capi")
    assert entry is not None
    assert entry.version == "1.0"
    assert entry.oauth_path == "/api/auth/meta"
    assert entry.oauth.start_path == "/api/auth/meta"
    assert entry.connector == "meta_capi"
    assert entry.event_destination is True
    field_names = {field.name for field in entry.fields}
    assert "event_name" in field_names
    assert "em" in field_names
    assert len(entry.required_metadata) == 2


def test_google_offline_parses_conversion_fields() -> None:
    entry = get_destination("google_offline_conversions")
    assert entry is not None
    gclid = next(field for field in entry.fields if field.name == "gclid")
    assert gclid.recommended is True
    event_name_stage = entry.per_stage.get("event_name")
    assert event_name_stage is not None
    assert event_name_stage.field == "conversion_action"
    assert event_name_stage.fill == "user"


def test_destination_ids() -> None:
    assert get_destination_ids() == {
        "meta_capi",
        "google_offline_conversions",
        "google_customer_match",
    }
