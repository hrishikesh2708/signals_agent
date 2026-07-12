"""CopilotKit / AG-UI mount point for the signals agent.

Exposes ``signals_agent`` at ``/api/v1/copilotkit/*``. JWT-authenticated via
``get_current_session`` (session-scoped Bearer token).

The :class:`copilotkit.CopilotKitRemoteEndpoint` and
:class:`copilotkit.LangGraphAGUIAgent` are initialised in
:func:`app.main.lifespan` and stored on ``app.state``.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies.auth import get_current_session
from app.models.agent_session import AgentSession

logger = logging.getLogger(__name__)

router = APIRouter()

AGENT_NAME = "signals_agent"
_AGENT_PATH_RE = re.compile(r"^agent/(?P<name>[a-zA-Z0-9_-]+)(?:/run)?$")


async def _get_sdk(request: Request):
    """Return the singleton CopilotKit SDK constructed in lifespan."""
    sdk = getattr(request.app.state, "copilotkit_sdk", None)
    if sdk is None:
        raise HTTPException(status_code=503, detail="agent not initialized")
    return sdk


def _get_langgraph_agent(request: Request):
    agent = getattr(request.app.state, "langgraph_agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="agent not initialized")
    return agent


def _is_info_request(body: dict[str, Any] | None, *, path: str, method: str) -> bool:
    if method == "GET" and path in ("", "info"):
        return True
    if body is None:
        return method in ("GET", "POST") and path in ("", "info")
    if body.get("method") == "info":
        return True
    if path == "info" and method == "POST":
        return True
    if body.get("method") in ("agent/run", "agent/connect", "agent/stop"):
        return False
    # Raw AG-UI RunAgentInput (HttpAgent) — not an info probe.
    if body.get("threadId") is not None and body.get("messages") is not None:
        return False
    if _AGENT_PATH_RE.match(path):
        return False
    return method in ("GET", "POST") and path in ("", "info")


def _extract_run_payload(body: dict[str, Any], *, path: str) -> dict[str, Any]:
    method = body.get("method")
    if method in ("agent/run", "agent/connect"):
        params = body.get("params") or {}
        requested = params.get("agentId") or params.get("agent_id")
        if requested and requested != AGENT_NAME:
            raise HTTPException(status_code=404, detail=f"Agent '{requested}' not found")
        return body.get("body") or {}

    if _AGENT_PATH_RE.match(path):
        match = _AGENT_PATH_RE.match(path)
        assert match is not None
        if match.group("name") != AGENT_NAME:
            raise HTTPException(status_code=404, detail=f"Agent '{match.group('name')}' not found")
        return body

    return body


def _copilotkit_sdk_version() -> str:
    try:
        import copilotkit

        return str(getattr(copilotkit, "COPILOTKIT_SDK_VERSION", "0.1.94"))
    except ImportError:
        return "0.1.94"


async def _handle_info(langgraph_agent) -> JSONResponse:
    sdk_version = _copilotkit_sdk_version()

    # CopilotKit v2 expects agents keyed by id, not a list.
    return JSONResponse(
        content={
            "version": sdk_version,
            "sdkVersion": sdk_version,
            "actions": [],
            "agents": {
                langgraph_agent.name: {
                    "name": langgraph_agent.name,
                    "description": langgraph_agent.description or "",
                    "type": "langgraph_agui",
                    "capabilities": {},
                }
            },
        }
    )


def _validate_project_header(request: Request, session: AgentSession) -> None:
    """If the client sends X-Project-Id, it must match the session's project."""
    header_pid = request.headers.get("x-project-id") or request.headers.get("X-Project-Id")
    if not header_pid:
        return
    try:
        header_uuid = UUID(header_pid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Project-Id") from exc
    if header_uuid != session.project_id:
        raise HTTPException(status_code=403, detail="Project mismatch")


def _inject_session_context(
    run_body: dict[str, Any],
    session: AgentSession,
    request: Request | None = None,
) -> dict[str, Any]:
    """Merge authenticated session identity into the AG-UI state payload.

    project_id resolution order:
    1. Already in state (client explicitly passed it)
    2. session.project_id (set when the session was created)
    3. X-Project-Id request header (sent by the frontend on every agent call)
    """
    state = dict(run_body.get("state") or {})
    state.setdefault("user_id", str(session.user_id))
    if not state.get("project_id"):
        if session.project_id:
            state["project_id"] = str(session.project_id)
        elif request:
            header_pid = request.headers.get("x-project-id") or request.headers.get(
                "X-Project-Id"
            )
            if header_pid:
                state["project_id"] = header_pid
    return {**run_body, "state": state}


async def _handle_agent_run(
    request: Request,
    langgraph_agent,
    body: dict[str, Any],
    *,
    path: str,
    session: AgentSession,
):
    run_body = _inject_session_context(
        _extract_run_payload(body, path=path), session, request
    )
    try:
        input_data = RunAgentInput.model_validate(run_body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run payload: {exc}") from exc

    accept_header = request.headers.get("accept") or "text/event-stream"
    encoder = EventEncoder(accept=accept_header)
    request_agent = langgraph_agent.clone()

    async def event_generator():
        async for event in request_agent.run(input_data):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
    )


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)
async def copilotkit_endpoint(
    request: Request,
    path: str,
    session: AgentSession = Depends(get_current_session),
    sdk=Depends(_get_sdk),
):
    """JWT-gated proxy into the CopilotKit / AG-UI runtime.

    Agent runs are streamed via :class:`copilotkit.LangGraphAGUIAgent` because
    that integration speaks AG-UI. Legacy CopilotKit execute routes are still
    delegated to the SDK handler for anything we do not recognise here.
    """
    langgraph_agent = _get_langgraph_agent(request)
    _validate_project_header(request, session)

    request.state.user_id = session.user_id
    request.state.session_id = session.id
    request.state.project_id = session.project_id

    logger.info(
        "copilotkit_request path=%s method=%s user_id=%s session_id=%s",
        path,
        request.method,
        session.user_id,
        session.id,
    )

    if request.method == "OPTIONS":
        return JSONResponse(content={})

    body: dict[str, Any] | None = None
    if request.method in ("POST", "PUT"):
        try:
            parsed = await request.json()
            body = parsed if isinstance(parsed, dict) else None
        except Exception:
            body = None

    if _is_info_request(body, path=path, method=request.method):
        return await _handle_info(langgraph_agent)

    if body and (
        body.get("method") in ("agent/run", "agent/connect")
        or (body.get("threadId") is not None and body.get("messages") is not None)
        or _AGENT_PATH_RE.match(path)
    ):
        return await _handle_agent_run(
            request, langgraph_agent, body, path=path, session=session
        )

    # Lazy import — avoid pulling the heavy copilotkit module on every cold start.
    from copilotkit.integrations.fastapi import handler as copilotkit_handler

    return await copilotkit_handler(request, sdk)
