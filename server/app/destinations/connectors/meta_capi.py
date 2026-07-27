from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.destinations.register import register_destination
from app.destinations.registry import env_value
from app.destinations.spec import Destination

_HTTP_TIMEOUT = httpx.Timeout(30.0)
_DEFAULT_META_SCOPE = "ads_management,business_management"


@dataclass(frozen=True)
class _DryRunResult:
    passed: bool
    detail: str


def _oauth_env(destination: Destination) -> dict[str, str]:
    oauth = destination.oauth
    return {
        "client_id": env_value(oauth.client_id_env),
        "client_secret": env_value(oauth.client_secret_env),
        "redirect_uri": env_value(oauth.redirect_uri_env),
        "scope": env_value(oauth.scope_env, default=_DEFAULT_META_SCOPE),
    }


@register_destination("meta_capi")
class MetaCapiConnector:
    def __init__(self, destination: Destination) -> None:
        self._destination = destination

    @property
    def id(self) -> str:
        return self._destination.id

    def auth_url(self, state: str, code_challenge: str | None = None) -> str:
        del code_challenge
        creds = _oauth_env(self._destination)
        params = {
            "client_id": creds["client_id"],
            "redirect_uri": creds["redirect_uri"],
            "state": state,
            "scope": creds["scope"],
            "response_type": "code",
        }
        return f"{self._destination.oauth.authorize_url}?{urlencode(params)}"

    async def exchange(self, code: str, code_verifier: str | None = None) -> dict:
        del code_verifier
        creds = _oauth_env(self._destination)
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(
                self._destination.oauth.token_url,
                params={
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                    "redirect_uri": creds["redirect_uri"],
                    "code": code,
                },
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Meta token exchange failed: {response.text}")
        data = response.json()
        if not isinstance(data, dict) or not data.get("access_token"):
            raise RuntimeError("Meta token exchange returned no access_token")
        return data

    async def refresh(self, refresh_token: str) -> dict:
        """Meta long-lived tokens are typically not refreshed via refresh_token."""
        del refresh_token
        raise RuntimeError("Meta CAPI does not support refresh_token exchange")

    async def dry_run(self, connection: dict, metadata: dict) -> _DryRunResult:
        del connection, metadata
        return _DryRunResult(passed=True, detail="Meta dry-run skipped (not wired yet).")

    def mock_metadata(self) -> dict[str, Any]:
        return {
            "pixelId": "123456789012345",
            "mock": True,
        }
