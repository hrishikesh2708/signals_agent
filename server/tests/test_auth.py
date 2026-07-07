def test_register_login_and_me(client) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "securepass",
            "name": "Test User",
        },
    )
    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["token_type"] == "bearer"
    assert register_payload["access_token"]
    assert register_payload["user"] == {
        "id": register_payload["user"]["id"],
        "email": "user@example.com",
        "name": "Test User",
    }

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "securepass",
        },
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["user"]["email"] == "user@example.com"

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_payload['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json() == login_payload["user"]


def test_register_duplicate_email_returns_conflict(client) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "securepass",
        "name": "First User",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Email already registered"


def test_login_with_invalid_credentials_returns_401(client) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "auth@example.com",
            "password": "securepass",
            "name": "Auth User",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "auth@example.com",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_without_token_returns_401(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
