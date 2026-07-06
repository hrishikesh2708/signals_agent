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
_DEFAULT_API_DOMAIN = "https://www.zohoapis.com"


def parse_fields(raw: dict[str, Any], schema: SchemaSpec) -> list[SourceField]:
    skip_types = set(schema.skip_types)
    fields: list[SourceField] = []
    for field in raw.get("fields") or []:
        if not isinstance(field, dict):
            continue
        field_type = str(field.get("data_type") or field.get("json_type") or "string")
        if field_type in skip_types:
            continue
        picklist_values = [
            str(value["display_value"])
            for value in field.get("pick_list_values") or []
            if isinstance(value, dict) and value.get("display_value") is not None
        ]
        api_name = str(field.get("api_name") or field.get("field_label") or "")
        if not api_name:
            continue
        fields.append(
            SourceField(
                name=api_name,
                label=str(field.get("field_label") or api_name),
                type=field_type,
                custom=bool(field.get("custom_field", False)),
                picklist_values=picklist_values,
            )
        )
    return fields


def _accounts_url(source: Source) -> str:
    oauth = source.oauth
    if oauth.accounts_url_env:
        return env_value(oauth.accounts_url_env, default=oauth.default_accounts_url or "")
    if oauth.default_accounts_url:
        return oauth.default_accounts_url
    raise RuntimeError(f"Source {source.id}: oauth.accounts_url_env or default_accounts_url is required")


def _format_url(template: str, source: Source) -> str:
    return template.format(accounts_url=_accounts_url(source).rstrip("/"))


def _oauth_env(source: Source) -> dict[str, str]:
    oauth = source.oauth
    return {
        "client_id": env_value(oauth.client_id_env),
        "client_secret": env_value(oauth.client_secret_env),
        "redirect_uri": env_value(oauth.redirect_uri_env),
        "scope": env_value(oauth.scope_env),
    }


def _api_base(instance_url: str) -> str:
    if instance_url.strip():
        return instance_url.rstrip("/")
    return _DEFAULT_API_DOMAIN


@register_source("zoho")
class ZohoConnector:
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
            "access_type": "offline",
            "prompt": "consent",
        }
        authorize = _format_url(self._source.oauth.authorize_url, self._source)
        return f"{authorize}?{urlencode(params)}"

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
        token_url = _format_url(self._source.oauth.token_url, self._source)
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(token_url, data=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Zoho token exchange failed: {response.text}")
        return response.json()

    async def refresh(self, refresh_token: str) -> dict:
        creds = _oauth_env(self._source)
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
        }
        token_url = _format_url(self._source.oauth.token_url, self._source)
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(token_url, data=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Zoho token refresh failed: {response.text}")
        return response.json()

    async def describe_object(
        self, instance_url: str, access_token: str, object_name: str
    ) -> list[SourceField]:
        api_version = self._source.schema.api_version
        if not api_version:
            raise RuntimeError(f"Source {self.id}: schema.api_version is required for describe")
        url = f"{_api_base(instance_url)}/crm/{api_version}/settings/fields"
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(
                url,
                params={"module": object_name},
                headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
            )
        if response.status_code == 401:
            raise SourceAuthError("Zoho access token expired")
        if response.status_code >= 400:
            raise RuntimeError(f"Zoho fields fetch failed: {response.text}")
        return parse_fields(response.json(), self._source.schema)
