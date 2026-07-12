from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_session, get_current_user
from app.graph.welcome import welcome_message
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


def _display_name(user: User) -> str:
    name = (user.name or "").strip()
    return name if name else "there"


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    request: Request,
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

    compiled_graph = getattr(request.app.state, "compiled_graph", None)
    if compiled_graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="agent not initialized",
        )

    session = AgentSession(
        project_id=project.id,
        user_id=current_user.id,
        name=body.name or DEFAULT_SESSION_NAME,
        status="active",
    )
    db.add(session)
    await db.flush()

    try:
        # as_node=scope_guard → next=() so the thread stays idle until runAgent.
        await compiled_graph.aupdate_state(
            {"configurable": {"thread_id": str(session.id)}},
            {"messages": [welcome_message(_display_name(current_user))]},
            as_node="scope_guard",
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to seed session thread",
        ) from exc

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
