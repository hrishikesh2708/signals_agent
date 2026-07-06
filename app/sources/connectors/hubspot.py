from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.sources.exceptions import SourceAuthError
from app.sources.protocol import SourceField
from app.sources.register import register_source
from app.sources.registry import env_value
from app.sources.spec import SchemaSpec, Source

_HTTP_TIMEOUT = httpx.Timeout(30.0)
_HUBSPOT_API = "https://api.hubapi.com"


def parse_properties(raw: dict[str, Any], schema: SchemaSpec) -> list[SourceField]:
    skip_types = set(schema.skip_types)
    fields: list[SourceField] = []
    for prop in raw.get("results") or []:
        if not isinstance(prop, dict):
            continue
        field_type = str(prop.get("type") or prop.get("fieldType") or "string")
        if field_type in skip_types:
            continue
        options = prop.get("options") or []
        picklist_values = [
            str(option["value"])
            for option in options
            if isinstance(option, dict) and option.get("value") is not None
        ]
        fields.append(
            SourceField(
                name=str(prop.get("name", "")),
                label=str(prop.get("label") or prop.get("name", "")),
                type=field_type,
                custom=not bool(prop.get("hubspotDefined", True)),
                picklist_values=picklist_values,
            )
        )
    return [field for field in fields if field.name]


def _oauth_env(source: Source) -> dict[str, str]:
    oauth = source.oauth
    return {
        "client_id": env_value(oauth.client_id_env),
        "client_secret": env_value(oauth.client_secret_env),
        "redirect_uri": env_value(oauth.redirect_uri_env),
        "scope": env_value(oauth.scope_env),
    }


@register_source("hubspot")
class HubSpotConnector:
    def __init__(self, source: Source) -> None:
        self._source = source
        self.id = source.id

    def auth_url(self, state: str, code_challenge: str | None = None) -> str:
        creds = _oauth_env(self._source)
        params = {
            "response_type": "code",
            "client_id": creds["client_id"],
            "redirect_uri": creds["redirect_uri"],
            "scope": creds["scope"],
            "state": state,
        }
        return f"{self._source.oauth.authorize_url}?{urlencode(params)}"

    async def exchange(self, code: str, code_verifier: str | None = None) -> dict:
        del code_verifier
        creds = _oauth_env(self._source)
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "redirect_uri": creds["redirect_uri"],
        }
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(self._source.oauth.token_url, data=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"HubSpot token exchange failed: {response.text}")
        return response.json()

    async def refresh(self, refresh_token: str) -> dict:
        creds = _oauth_env(self._source)
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
        }
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(self._source.oauth.token_url, data=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"HubSpot token refresh failed: {response.text}")
        return response.json()

    async def describe_object(
        self, instance_url: str, access_token: str, object_name: str
    ) -> list[SourceField]:
        del instance_url
        url = f"{_HUBSPOT_API}/crm/v3/properties/{object_name}"
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code == 401:
            raise SourceAuthError("HubSpot access token expired")
        if response.status_code >= 400:
            raise RuntimeError(f"HubSpot properties fetch failed: {response.text}")
        return parse_properties(response.json(), self._source.schema)
