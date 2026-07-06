from __future__ import annotations

from typing import Protocol


class DryRunResult(Protocol):
    passed: bool
    detail: str


class DestinationConnector(Protocol):
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

    async def dry_run(self, connection: dict, metadata: dict) -> DryRunResult:
        """Optional live API ping during setup validation."""
        ...

    def mock_metadata(self) -> dict:
        """Default metadata when mock connect is used."""
        ...
