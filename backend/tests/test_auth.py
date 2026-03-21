import pytest
from httpx import AsyncClient


# ── /register ────────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "securepass"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_register_email_case_insensitive(client: AsyncClient):
    """Registering with different casing of the same email must return 409."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "Bob@Example.Com", "password": "securepass"},
    )
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "anotherpass"},
    )
    assert response.status_code == 409


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "securepass"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


async def test_register_short_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 422


async def test_register_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "securepass"},
    )
    assert response.status_code == 422


# ── /login ────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "securepass"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "securepass"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": "securepass"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrongpw@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "securepass"},
    )
    assert response.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────

async def test_get_me(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "securepass"},
    )
    token = reg.json()["access_token"]
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["is_active"] is True
    assert "hashed_password" not in data


async def test_get_me_no_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_get_me_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401


async def test_get_me_with_refresh_token_rejected(client: AsyncClient):
    """Passing a refresh token to a protected endpoint must return 401."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongtype@example.com", "password": "securepass"},
    )
    refresh_token = reg.json()["refresh_token"]
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == 401


# ── /refresh ──────────────────────────────────────────────────────────────────

async def test_refresh_token(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "securepass"},
    )
    old_refresh = reg.json()["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # Rotated token must differ from the original.
    assert data["refresh_token"] != old_refresh


async def test_refresh_with_revoked_token(client: AsyncClient):
    """A refresh token consumed once must be rejected on a second use."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "revoked@example.com", "password": "securepass"},
    )
    old_refresh = reg.json()["refresh_token"]
    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert response.status_code == 401


async def test_refresh_with_access_token_rejected(client: AsyncClient):
    """Sending an access token to /refresh must return 401."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "accesstype@example.com", "password": "securepass"},
    )
    access_token = reg.json()["access_token"]
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert response.status_code == 401


async def test_new_access_token_works_after_refresh(client: AsyncClient):
    """The new access token issued after a refresh must be accepted by /me."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "newtoken@example.com", "password": "securepass"},
    )
    old_refresh = reg.json()["refresh_token"]
    new_tokens = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    ).json()
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "newtoken@example.com"
