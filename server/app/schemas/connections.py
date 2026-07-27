from pydantic import BaseModel, Field


class SourceAuthorizeResponse(BaseModel):
    auth_url: str
    state: str  # OAuth CSRF — not agent state


class SourceConnectionStatusResponse(BaseModel):
    connected: bool
    instance_url: str | None = None
    source_id: str


class DestinationAuthorizeResponse(BaseModel):
    auth_url: str
    state: str


class DestinationConnectionStatusResponse(BaseModel):
    connected: bool
    destination_id: str


class DestinationMockConnectRequest(BaseModel):
    """Mock-connect body. Meta uses pixel_id + access_token; Google uses refresh_token."""

    pixel_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
