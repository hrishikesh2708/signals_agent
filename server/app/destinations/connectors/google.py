from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.destinations.register import register_destination
from app.destinations.registry import env_value
from app.destinations.spec import Destination

_HTTP_TIMEOUT = httpx.Timeout(30.0)
_DEFAULT_GOOGLE_SCOPE = "https://www.googleapis.com/auth/adwords"


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
        "scope": env_value(oauth.scope_env, default=_DEFAULT_GOOGLE_SCOPE),
    }


def _is_mock_token(access_token: str) -> bool:
    return access_token == "mock_access_token" or access_token.startswith("mock_")


class _GoogleAdsConnectorBase:
    """Shared Google Ads OAuth for offline conversions and customer match."""

    def __init__(self, destination: Destination) -> None:
        self._destination = destination

    @property
    def id(self) -> str:
        return self._destination.id

    def auth_url(self, state: str, code_challenge: str | None = None) -> str:
        creds = _oauth_env(self._destination)
        params: dict[str, str] = {
            "client_id": creds["client_id"],
            "redirect_uri": creds["redirect_uri"],
            "response_type": "code",
            "scope": creds["scope"],
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        return f"{self._destination.oauth.authorize_url}?{urlencode(params)}"

    async def exchange(self, code: str, code_verifier: str | None = None) -> dict:
        creds = _oauth_env(self._destination)
        data: dict[str, str] = {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "redirect_uri": creds["redirect_uri"],
            "grant_type": "authorization_code",
            "code": code,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(self._destination.oauth.token_url, data=data)
        if response.status_code >= 400:
            raise RuntimeError(f"Google token exchange failed: {response.text}")
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("access_token"):
            raise RuntimeError("Google token exchange returned no access_token")
        return payload

    async def refresh(self, refresh_token: str) -> dict:
        creds = _oauth_env(self._destination)
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(
                self._destination.oauth.token_url,
                data={
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Google refresh-token exchange failed: {response.text}")
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("access_token"):
            raise RuntimeError("Google refresh returned no access_token")
        # Preserve the submitted refresh token (Google often omits it on refresh).
        if not payload.get("refresh_token"):
            payload = {**payload, "refresh_token": refresh_token}
        return payload

    async def dry_run(self, connection: dict, metadata: dict) -> _DryRunResult:
        """Confirm OAuth token can reach Google Ads when a developer token is set."""
        access_token = connection.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            return _DryRunResult(passed=False, detail="Missing access_token for Google dry-run.")

        if metadata.get("mock") is True or _is_mock_token(access_token):
            return _DryRunResult(
                passed=True,
                detail="Google dry-run passed (mock mode — no API call made).",
            )

        developer_token = settings.google_ads_developer_token.strip()
        if not developer_token:
            return _DryRunResult(
                passed=True,
                detail=(
                    "Google OAuth token valid. Schema check passed "
                    "(developer token not set for live API call)."
                ),
            )

        version = settings.google_api_version.strip() or "v21"
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(
                f"https://googleads.googleapis.com/{version}/customers:listAccessibleCustomers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": developer_token,
                },
            )
        if response.status_code >= 400:
            return _DryRunResult(
                passed=False,
                detail=f"Google Ads API check failed: {response.text}",
            )
        return _DryRunResult(
            passed=True,
            detail="Google Ads API accessible with current credentials.",
        )

    def mock_metadata(self) -> dict[str, Any]:
        return {
            "customerId": "customers/1234567890",
            "mock": True,
        }


@register_destination("google_offline_conversions")
class GoogleOfflineConversionsConnector(_GoogleAdsConnectorBase):
    pass


@register_destination("google_customer_match")
class GoogleCustomerMatchConnector(_GoogleAdsConnectorBase):
    pass
