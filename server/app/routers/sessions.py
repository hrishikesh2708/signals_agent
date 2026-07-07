from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_session, get_current_user
from app.models.agent_session import AgentSession
from app.models.project import Project
from app.models.user import User
from app.schemas.session import AgentSessionResponse, SessionCreate, SessionResponse
from app.services.auth_service import create_session_token

router = APIRouter(tags=["sessions"])

DEFAULT_SESSION_NAME = "New session"


def _session_response(session: AgentSession) -> AgentSessionResponse:
    return AgentSessionResponse(
        session_id=str(session.id),
        project_id=str(session.project_id),
        user_id=str(session.user_id),
        name=session.name,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    result = await db.execute(
        select(Project).where(
            Project.id == body.project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    session = AgentSession(
        project_id=project.id,
        user_id=current_user.id,
        name=body.name or DEFAULT_SESSION_NAME,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        session_id=str(session.id),
        token=create_session_token(str(session.id)),
        name=session.name,
    )


@router.get("/session/me", response_model=AgentSessionResponse)
async def session_me(
    current_session: AgentSession = Depends(get_current_session),
) -> AgentSessionResponse:
    return _session_response(current_session)
