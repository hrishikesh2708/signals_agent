from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    project_id: UUID
    name: str | None = Field(default=None, max_length=255)


class SessionResponse(BaseModel):
    session_id: str
    token: str
    token_type: str = "bearer"
    name: str


class AgentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    project_id: str
    user_id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
