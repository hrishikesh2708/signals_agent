from __future__ import annotations

import asyncio

import pytest

from app.sources import get_connector, get_source, get_source_registry, resolve_source
from app.sources.connectors import salesforce as salesforce_mod
from app.sources.exceptions import SourceRegistryError
from app.sources.protocol import SourceField
from app.sources.spec import SchemaSpec


def test_loads_three_enabled_sources_at_startup() -> None:
    registry = get_source_registry()
    assert {source.id for source in registry.sources} == {"salesforce", "hubspot", "zoho"}


def test_each_enabled_source_has_connector() -> None:
    registry = get_source_registry()
    for source in registry.sources:
        connector = registry.get_connector(source.id)
        assert connector.id == source.id


def test_salesforce_catalog_is_complete() -> None:
    source = get_source("salesforce")
    assert source is not None
    assert source.oauth.start_path == "/api/auth/salesforce"
    assert source.oauth.pkce is True
    assert "Opportunity" in source.objects_common
    assert source.related_identity_for("Opportunity") is not None
    assert source.schema.api_version == "v59.0"


def test_hubspot_catalog_oauth_paths() -> None:
    source = get_source("hubspot")
    assert source is not None
    assert source.oauth.start_path == "/api/auth/source/hubspot"
    assert source.oauth.pkce is False


def test_resolve_source_aliases() -> None:
    assert resolve_source("sfdc") == "salesforce"
    assert resolve_source("hub spot") == "hubspot"
    assert resolve_source("zoho crm") == "zoho"
    assert resolve_source("unknown") is None


def test_get_connector_returns_salesforce_adapter() -> None:
    connector = get_connector("salesforce")
    assert connector.id == "salesforce"


def test_salesforce_parse_describe_skips_address_types() -> None:
    schema = SchemaSpec(
        skip_types=("address", "location"),
        expose=("name", "label", "type", "custom", "picklist_values"),
        identity_field_patterns=("email", "phone", "mobile"),
        api_version="v59.0",
    )
    raw = {
        "fields": [
            {
                "name": "Email",
                "label": "Email",
                "type": "email",
                "custom": False,
                "picklistValues": [],
            },
            {
                "name": "BillingAddress",
                "label": "Billing Address",
                "type": "address",
                "custom": False,
                "picklistValues": [],
            },
        ]
    }
    fields = salesforce_mod.parse_describe(raw, schema)
    assert [field.name for field in fields] == ["Email"]


def test_salesforce_enrich_fields_adds_related_contact_fields() -> None:
    source = get_source("salesforce")
    assert source is not None

    base_fields = [
        SourceField(
            name="Amount",
            label="Amount",
            type="currency",
            custom=False,
        )
    ]

    async def fetch_related(_object_name: str):
        return [
            SourceField(
                name="Email",
                label="Email",
                type="email",
                custom=False,
            ),
            SourceField(
                name="Phone",
                label="Phone",
                type="phone",
                custom=False,
            ),
        ]

    enriched = asyncio.run(
        salesforce_mod.enrich_fields(
            base_fields,
            "Opportunity",
            source,
            fetch_related,
        )
    )
    names = {field.name for field in enriched}
    assert "Contact.Email" in names
    assert "Contact.Phone" in names


def test_auth_url_requires_env_at_call_time_not_import() -> None:
    connector = get_connector("salesforce")
    with pytest.raises(SourceRegistryError):
        connector.auth_url("test-state", code_challenge="challenge")
