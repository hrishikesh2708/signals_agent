import uuid


def _register_and_get_token(client, *, email: str | None = None) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email or f"sessions-{uuid.uuid4()}@example.com",
            "password": "securepass",
            "name": "Session User",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_project(client, user_token: str, *, name: str = "Session Project") -> str:
    response = client.post(
        "/api/v1/projects",
        headers=_auth_headers(user_token),
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_session_and_access_guarded_endpoint(client) -> None:
    user_token = _register_and_get_token(client)
    project_id = _create_project(client, user_token)

    create_response = client.post(
        "/api/v1/auth/session",
        headers=_auth_headers(user_token),
        json={"project_id": project_id, "name": "Setup run 1"},
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["session_id"]
    assert payload["token"]
    assert payload["token_type"] == "bearer"
    assert payload["name"] == "Setup run 1"

    me_response = client.get(
        "/api/v1/auth/session/me",
        headers=_auth_headers(payload["token"]),
    )
    assert me_response.status_code == 200
    session = me_response.json()
    assert session["session_id"] == payload["session_id"]
    assert session["project_id"] == project_id
    assert session["name"] == "Setup run 1"
    assert session["status"] == "active"


def test_create_session_defaults_name(client) -> None:
    user_token = _register_and_get_token(client)
    project_id = _create_project(client, user_token)

    response = client.post(
        "/api/v1/auth/session",
        headers=_auth_headers(user_token),
        json={"project_id": project_id},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "New session"


def test_create_session_for_other_users_project_returns_404(client) -> None:
    owner_token = _register_and_get_token(client)
    project_id = _create_project(client, owner_token)

    other_token = _register_and_get_token(client, email=f"other-{uuid.uuid4()}@example.com")
    response = client.post(
        "/api/v1/auth/session",
        headers=_auth_headers(other_token),
        json={"project_id": project_id},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_create_session_requires_user_auth(client) -> None:
    response = client.post(
        "/api/v1/auth/session",
        json={"project_id": str(uuid.uuid4())},
    )
    assert response.status_code == 401


def test_session_me_rejects_user_token(client) -> None:
    user_token = _register_and_get_token(client)
    response = client.get("/api/v1/auth/session/me", headers=_auth_headers(user_token))
    assert response.status_code == 401
    assert response.json()["detail"] == "Session not found"


def test_session_me_rejects_invalid_token(client) -> None:
    response = client.get(
        "/api/v1/auth/session/me",
        headers=_auth_headers("not-a-valid-token"),
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
