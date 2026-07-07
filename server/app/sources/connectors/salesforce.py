from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode

import httpx

from app.sources.exceptions import SourceAuthError
from app.sources.protocol import SourceField
from app.sources.register import register_source
from app.sources.registry import env_value
from app.sources.spec import SchemaSpec, Source

_HTTP_TIMEOUT = httpx.Timeout(30.0)


def parse_describe(raw: dict[str, Any], schema: SchemaSpec) -> list[SourceField]:
    skip_types = set(schema.skip_types)
    fields: list[SourceField] = []
    for field in raw.get("fields") or []:
        if not isinstance(field, dict):
            continue
        field_type = str(field.get("type", ""))
        if field_type in skip_types:
            continue
        picklist_values = [
            str(value["value"])
            for value in field.get("picklistValues") or []
            if isinstance(value, dict)
            and value.get("active", True)
            and value.get("value")
        ]
        fields.append(
            SourceField(
                name=str(field["name"]),
                label=str(field.get("label", field["name"])),
                type=field_type,
                custom=bool(field.get("custom", False)),
                picklist_values=picklist_values,
            )
        )
    return fields


def is_identity_field(field_name: str, schema: SchemaSpec) -> bool:
    lowered = field_name.lower()
    return any(pattern in lowered for pattern in schema.identity_field_patterns)


def object_has_identity(fields: list[SourceField], schema: SchemaSpec) -> bool:
    return any(is_identity_field(field.name, schema) for field in fields)


def to_safe_dicts(fields: list[SourceField], schema: SchemaSpec) -> list[dict[str, Any]]:
    allowed = set(schema.expose)
    result: list[dict[str, Any]] = []
    for field in fields:
        payload = field.model_dump()
        result.append({key: payload[key] for key in schema.expose if key in allowed})
    return result


def fingerprint(fields: list[SourceField], schema: SchemaSpec) -> str:
    safe = to_safe_dicts(fields, schema)
    return str(hash(tuple(sorted(item["name"] for item in safe))))


async def enrich_fields(
    fields: list[SourceField],
    object_name: str,
    source: Source,
    fetch_object_fields: Callable[[str], Awaitable[list[SourceField]]],
) -> list[SourceField]:
    spec = source.related_identity_for(object_name)
    if spec is None or object_has_identity(fields, source.schema):
        return list(fields)

    enriched = list(fields)
    related_fields = await fetch_object_fields(spec.related_object)
    wanted = set(spec.surface_fields)
    for related_field in related_fields:
        if related_field.name in wanted:
            enriched.append(
                SourceField(
                    name=f"{spec.related_object}.{related_field.name}",
                    label=f"{spec.related_object}: {related_field.label}",
                    type=related_field.type,
                    custom=related_field.custom,
                    picklist_values=list(related_field.picklist_values),
                )
            )
    return enriched


def _login_url(source: Source) -> str:
    oauth = source.oauth
    if oauth.login_url_env:
        return env_value(oauth.login_url_env, default=oauth.default_login_url or "")
    if oauth.default_login_url:
        return oauth.default_login_url
    raise RuntimeError(f"Source {source.id}: oauth.login_url_env or default_login_url is required")


def _format_url(template: str, source: Source) -> str:
    return template.format(login_url=_login_url(source).rstrip("/"))


def _oauth_env(source: Source) -> dict[str, str]:
    oauth = source.oauth
    return {
        "client_id": env_value(oauth.client_id_env),
        "client_secret": env_value(oauth.client_secret_env),
        "redirect_uri": env_value(oauth.redirect_uri_env),
        "scope": env_value(oauth.scope_env),
    }


@register_source("salesforce")
class SalesforceConnector:
    def __init__(self, source: Source) -> None:
        self._source = source
        self.id = source.id

    def auth_url(self, state: str, code_challenge: str | None = None) -> str:
        oauth = self._source.oauth
        if oauth.pkce and not code_challenge:
            raise ValueError("Salesforce OAuth requires PKCE (code_challenge)")
        creds = _oauth_env(self._source)
        params = {
            "response_type": "code",
            "client_id": creds["client_id"],
            "redirect_uri": creds["redirect_uri"],
            "scope": creds["scope"],
            "state": state,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        authorize = _format_url(oauth.authorize_url, self._source)
        return f"{authorize}?{urlencode(params)}"

    async def exchange(self, code: str, code_verifier: str | None = None) -> dict:
        oauth = self._source.oauth
        if oauth.pkce and not code_verifier:
            raise ValueError("Salesforce token exchange requires code_verifier")
        creds = _oauth_env(self._source)
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "redirect_uri": creds["redirect_uri"],
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier
        token_url = _format_url(oauth.token_url, self._source)
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(token_url, data=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Salesforce token exchange failed: {response.text}")
        return response.json()

    async def refresh(self, refresh_token: str) -> dict:
        creds = _oauth_env(self._source)
        oauth = self._source.oauth
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
        }
        token_url = _format_url(oauth.token_url, self._source)
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(token_url, data=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Salesforce token refresh failed: {response.text}")
        return response.json()

    async def _fetch_object_fields(
        self, instance_url: str, access_token: str, object_name: str
    ) -> list[SourceField]:
        api_version = self._source.schema.api_version
        if not api_version:
            raise RuntimeError(f"Source {self.id}: schema.api_version is required for describe")
        url = f"{instance_url.rstrip('/')}/services/data/{api_version}/sobjects/{object_name}/describe"
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code == 401:
            raise SourceAuthError("Salesforce access token expired")
        if response.status_code >= 400:
            raise RuntimeError(f"Salesforce describe failed: {response.text}")
        return parse_describe(response.json(), self._source.schema)

    async def describe_object(
        self, instance_url: str, access_token: str, object_name: str
    ) -> list[SourceField]:
        fields = await self._fetch_object_fields(instance_url, access_token, object_name)

        async def fetch_related(related_object: str) -> list[SourceField]:
            return await self._fetch_object_fields(instance_url, access_token, related_object)

        return await enrich_fields(fields, object_name, self._source, fetch_related)
