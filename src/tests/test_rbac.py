from __future__ import annotations


def _login_admin(client):
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "AdminPass123!"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_admin_can_list_roles(client):
    headers = _login_admin(client)
    res = client.get("/api/v1/rbac/roles", headers=headers)
    assert res.status_code == 200
    role_names = {r["name"] for r in res.json()}
    assert {"admin", "user"} <= role_names


def test_non_admin_cannot_create_roles(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "username": "bob",
            "password": "BobPass123!",
        },
    )
    tokens = client.post(
        "/api/v1/auth/login",
        data={"username": "bob", "password": "BobPass123!"},
    ).json()

    res = client.post(
        "/api/v1/rbac/roles",
        json={"name": "editor", "permission_ids": []},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert res.status_code == 403


def test_admin_can_create_role(client):
    headers = _login_admin(client)
    res = client.post(
        "/api/v1/rbac/roles",
        json={"name": "editor", "description": "Editors", "permission_ids": []},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["name"] == "editor"
