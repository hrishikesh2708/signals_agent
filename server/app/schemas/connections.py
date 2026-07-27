from pydantic import BaseModel


class SourceAuthorizeResponse(BaseModel):
    auth_url: str
    state: str  # OAuth CSRF — not agent state


class SourceConnectionStatusResponse(BaseModel):
    connected: bool
    instance_url: str | None = None
    source_id: str
