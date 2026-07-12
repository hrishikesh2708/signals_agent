"""Tests for CopilotKit mount + JWT session gate."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from ag_ui.core.events import RunFinishedEvent

from app.models.agent_session import AgentSession
from app.routers.copilotkit import (
    AGENT_NAME,
    _inject_session_context,
    _is_info_request,
)


def _register_and_get_token(client, *, email: str | None = None) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email or f"copilot-{uuid.uuid4()}@example.com",
            "password": "securepass",
            "name": "Copilot User",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _auth_headers(token: str, *, project_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if project_id is not None:
        headers["X-Project-Id"] = project_id
    return headers


def _create_project(client, user_token: str) -> str:
    response = client.post(
        "/api/v1/projects",
        headers=_auth_headers(user_token),
        json={"name": "Copilot Project"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_session(client, user_token: str, project_id: str) -> dict:
    response = client.post(
        "/api/v1/auth/session",
        headers=_auth_headers(user_token),
        json={"project_id": project_id, "name": "Chat 1"},
    )
    assert response.status_code == 201
    return response.json()


def test_is_info_request_detects_probes() -> None:
    assert _is_info_request(None, path="", method="GET")
    assert _is_info_request({"method": "info"}, path="", method="POST")
    assert not _is_info_request(
        {"threadId": "t", "messages": []}, path="", method="POST"
    )
    assert not _is_info_request(
        {"method": "agent/run"}, path="", method="POST"
    )


def test_inject_session_context_sets_user_and_project() -> None:
    session = AgentSession(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="t",
        status="active",
    )
    result = _inject_session_context({"state": {}, "threadId": "t"}, session)
    assert result["state"]["user_id"] == str(session.user_id)
    assert result["state"]["project_id"] == str(session.project_id)


def test_inject_session_context_preserves_existing_project() -> None:
    session = AgentSession(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="t",
        status="active",
    )
    result = _inject_session_context(
        {"state": {"project_id": "client-project"}, "threadId": "t"},
        session,
    )
    assert result["state"]["project_id"] == "client-project"
    assert result["state"]["user_id"] == str(session.user_id)


def test_copilotkit_info_requires_session_auth(client) -> None:
    response = client.get("/api/v1/copilotkit/info")
    assert response.status_code == 401


def test_copilotkit_info_rejects_user_token(client) -> None:
    user_token = _register_and_get_token(client)
    response = client.get(
        "/api/v1/copilotkit/info",
        headers=_auth_headers(user_token),
    )
    assert response.status_code == 401


def test_copilotkit_info_with_session_token(client) -> None:
    user_token = _register_and_get_token(client)
    project_id = _create_project(client, user_token)
    session = _create_session(client, user_token, project_id)

    response = client.get(
        "/api/v1/copilotkit/info",
        headers=_auth_headers(session["token"], project_id=project_id),
    )
    assert response.status_code == 200
    payload = response.json()
    assert AGENT_NAME in payload["agents"]
    assert payload["agents"][AGENT_NAME]["name"] == AGENT_NAME
    assert payload["agents"][AGENT_NAME]["type"] == "langgraph_agui"


def test_copilotkit_rejects_mismatched_project_header(client) -> None:
    user_token = _register_and_get_token(client)
    project_id = _create_project(client, user_token)
    session = _create_session(client, user_token, project_id)

    response = client.get(
        "/api/v1/copilotkit/info",
        headers=_auth_headers(session["token"], project_id=str(uuid.uuid4())),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Project mismatch"


def test_copilotkit_agent_run_streams(client) -> None:
    """Agent run path streams SSE when LangGraphAGUIAgent.run yields events."""
    user_token = _register_and_get_token(client)
    project_id = _create_project(client, user_token)
    session = _create_session(client, user_token, project_id)
    thread_id = session["session_id"]
    run_id = str(uuid.uuid4())

    async def _fake_run(_input):
        yield RunFinishedEvent(thread_id=thread_id, run_id=run_id)

    fake_clone = MagicMock()
    fake_clone.run = _fake_run
    fake_agent = SimpleNamespace(
        name=AGENT_NAME,
        description="test",
        clone=MagicMock(return_value=fake_clone),
    )
    client.app.state.langgraph_agent = fake_agent

    response = client.post(
        f"/api/v1/copilotkit/agent/{AGENT_NAME}/run",
        headers={
            **_auth_headers(session["token"], project_id=project_id),
            "Accept": "text/event-stream",
        },
        json={
            "threadId": thread_id,
            "runId": run_id,
            "state": {},
            "messages": [{"id": "m1", "role": "user", "content": "hi"}],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert response.text  # SSE body present


def test_copilotkit_resume_uses_same_thread_id(client) -> None:
    """HITL resume payloads reuse session_id as threadId through the run path."""
    user_token = _register_and_get_token(client)
    project_id = _create_project(client, user_token)
    session = _create_session(client, user_token, project_id)
    thread_id = session["session_id"]
    run_id = str(uuid.uuid4())
    captured: dict = {}

    async def _fake_run(input_data):
        captured["thread_id"] = input_data.thread_id
        captured["resume"] = input_data.resume
        captured["state"] = input_data.state
        yield RunFinishedEvent(thread_id=thread_id, run_id=run_id)

    fake_clone = MagicMock()
    fake_clone.run = _fake_run
    fake_agent = SimpleNamespace(
        name=AGENT_NAME,
        description="test",
        clone=MagicMock(return_value=fake_clone),
    )
    client.app.state.langgraph_agent = fake_agent

    interrupt_id = str(uuid.uuid4())
    response = client.post(
        f"/api/v1/copilotkit/agent/{AGENT_NAME}/run",
        headers=_auth_headers(session["token"], project_id=project_id),
        json={
            "threadId": thread_id,
            "runId": run_id,
            "state": {},
            "messages": [{"id": "m1", "role": "user", "content": "resume"}],
            "tools": [],
            "context": [],
            "forwardedProps": {},
            "resume": [
                {
                    "interruptId": interrupt_id,
                    "status": "resolved",
                    "payload": {"choice": "salesforce"},
                }
            ],
        },
    )
    assert response.status_code == 200
    assert captured["thread_id"] == thread_id
    assert captured["resume"] is not None
    assert captured["resume"][0].interrupt_id == interrupt_id
    assert captured["state"]["user_id"]
    assert captured["state"]["project_id"] == project_id


def test_copilotkit_unknown_agent_returns_404(client) -> None:
    user_token = _register_and_get_token(client)
    project_id = _create_project(client, user_token)
    session = _create_session(client, user_token, project_id)

    response = client.post(
        "/api/v1/copilotkit/agent/other_agent/run",
        headers=_auth_headers(session["token"], project_id=project_id),
        json={
            "threadId": session["session_id"],
            "runId": str(uuid.uuid4()),
            "state": {},
            "messages": [{"id": "m1", "role": "user", "content": "hi"}],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    assert response.status_code == 404
