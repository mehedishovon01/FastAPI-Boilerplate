"""Tests for the PATCH semantics on /users/me and /users/{id}."""
from __future__ import annotations


# ---------- helpers ----------

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
    res = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _admin_headers(client):
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# ---------- PATCH semantics ----------

def test_patch_me_omitted_field_is_untouched(client):
    """Sending only `full_name` must not affect `email`."""
    _register(client)
    headers = _login(client)
    res = client.patch(
        "/api/v1/users/me",
        json={"full_name": "Alice Updated"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["full_name"] == "Alice Updated"
    assert body["email"] == "alice@example.com"  # untouched


def test_patch_me_explicit_null_clears_nullable_field(client):
    """Sending `{"full_name": null}` must actually clear the field."""
    _register(client)
    headers = _login(client)
    res = client.patch(
        "/api/v1/users/me",
        json={"full_name": None},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["full_name"] is None


def test_patch_me_cannot_self_promote_or_deactivate(client):
    """Privileged fields are not part of UserSelfUpdate; they're ignored."""
    _register(client)
    headers = _login(client)
    res = client.patch(
        "/api/v1/users/me",
        json={"is_active": False, "is_superuser": True, "role_ids": [1]},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_active"] is True       # not deactivated
    assert body["is_superuser"] is False   # not promoted


def test_admin_patch_can_deactivate_user(client):
    """Admins reach `is_active` through /users/{id}, not /users/me."""
    _register(client)
    target = client.get("/api/v1/users/me", headers=_login(client)).json()

    res = client.patch(
        f"/api/v1/users/{target['id']}",
        json={"is_active": False},
        headers=_admin_headers(client),
    )
    assert res.status_code == 200, res.text
    assert res.json()["is_active"] is False


def test_admin_patch_email_uniqueness_is_enforced(client):
    """Patching to an email already in use must 409."""
    _register(client)  # alice
    _register(client, email="bob@example.com", username="bob")

    alice = client.get("/api/v1/users/me", headers=_login(client)).json()

    res = client.patch(
        f"/api/v1/users/{alice['id']}",
        json={"email": "bob@example.com"},
        headers=_admin_headers(client),
    )
    assert res.status_code == 409, res.text


def test_admin_patch_assigns_roles(client):
    """Sending role_ids must replace the user's roles."""
    _register(client)
    alice = client.get("/api/v1/users/me", headers=_login(client)).json()

    admin_headers = _admin_headers(client)
    roles = client.get("/api/v1/rbac/roles", headers=admin_headers).json()
    admin_role_id = next(r["id"] for r in roles if r["name"] == "admin")

    res = client.patch(
        f"/api/v1/users/{alice['id']}",
        json={"role_ids": [admin_role_id]},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    assigned = {r["name"] for r in res.json()["roles"]}
    assert assigned == {"admin"}
