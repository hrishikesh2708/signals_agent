import uuid


def _register_and_get_token(client, *, email: str | None = None) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email or f"projects-{uuid.uuid4()}@example.com",
            "password": "securepass",
            "name": "Project User",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_list_and_get_project(client) -> None:
    token = _register_and_get_token(client)
    headers = _auth_headers(token)

    create_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Acme Signals", "description": "Primary workspace"},
    )
    assert create_response.status_code == 201
    project = create_response.json()
    assert project["name"] == "Acme Signals"
    assert project["description"] == "Primary workspace"
    assert project["id"]
    assert project["user_id"]

    list_response = client.get("/api/v1/projects", headers=headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == project["id"]

    get_response = client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json() == project


def test_create_duplicate_project_name_returns_conflict(client) -> None:
    token = _register_and_get_token(client)
    headers = _auth_headers(token)
    payload = {"name": "Duplicate Name"}

    assert client.post("/api/v1/projects", headers=headers, json=payload).status_code == 201
    duplicate = client.post("/api/v1/projects", headers=headers, json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A project with this name already exists"


def test_get_other_users_project_returns_404(client) -> None:
    owner_token = _register_and_get_token(client)
    owner_headers = _auth_headers(owner_token)
    create_response = client.post(
        "/api/v1/projects",
        headers=owner_headers,
        json={"name": "Owner Project"},
    )
    project_id = create_response.json()["id"]

    other_register = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"other-{uuid.uuid4()}@example.com",
            "password": "securepass",
            "name": "Other User",
        },
    )
    other_headers = _auth_headers(other_register.json()["access_token"])

    response = client.get(f"/api/v1/projects/{project_id}", headers=other_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_delete_project(client) -> None:
    token = _register_and_get_token(client)
    headers = _auth_headers(token)
    create_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Temporary Project"},
    )
    project_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_response.status_code == 404


def test_projects_require_auth(client) -> None:
    assert client.get("/api/v1/projects").status_code == 401
    assert client.post("/api/v1/projects", json={"name": "No Auth"}).status_code == 401
