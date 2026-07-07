from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class SourceField(BaseModel):
    """Normalized source-field metadata every connector returns."""

    name: str
    label: str
    type: str
    custom: bool
    picklist_values: list[str] = Field(default_factory=list)


class SourceConnector(Protocol):
    id: str

    def auth_url(self, state: str, code_challenge: str | None = None) -> str:
        """OAuth authorize URL for the browser handoff."""
        ...

    async def exchange(self, code: str, code_verifier: str | None = None) -> dict:
        """Exchange an authorization code for tokens."""
        ...

    async def refresh(self, refresh_token: str) -> dict:
        """Mint a fresh access token from a refresh token."""
        ...

    async def describe_object(
        self, instance_url: str, access_token: str, object_name: str
    ) -> list[SourceField]:
        """Field metadata for an object. Metadata only — never record data."""
        ...
