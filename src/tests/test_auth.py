from __future__ import annotations


def _register(client, **overrides):
    payload = {
        "email": "alice@example.com",
        "username": "alice",
        "full_name": "Alice",
        "password": "SuperSecret1!",
        **overrides,
    }
    return client.post("/api/v1/auth/register", json=payload)


def _login(client, username="alice", password="SuperSecret1!"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_and_login(client):
    res = _register(client)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "alice@example.com"
    assert "hashed_password" not in body

    res = _login(client)
    assert res.status_code == 200, res.text
    tokens = res.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]


def test_register_duplicate_email_conflicts(client):
    _register(client)
    res = _register(client, username="alice2")
    assert res.status_code == 409


def test_me_requires_auth(client):
    res = client.get("/api/v1/users/me")
    assert res.status_code == 401


def test_me_returns_current_user(client):
    _register(client)
    tokens = _login(client).json()
    res = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert res.status_code == 200
    assert res.json()["username"] == "alice"


def test_refresh_token_returns_new_access_token(client):
    _register(client)
    tokens = _login(client).json()
    res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_change_password_flow(client):
    _register(client)
    tokens = _login(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    res = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "SuperSecret1!", "new_password": "EvenBetter2@"},
        headers=headers,
    )
    assert res.status_code == 204

    assert _login(client).status_code == 401
    assert _login(client, password="EvenBetter2@").status_code == 200
