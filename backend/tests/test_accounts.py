import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_and_token(client: AsyncClient, email: str = "user@example.com") -> str:
    reg = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "securepass"}
    )
    return reg.json()["access_token"]


async def _create_account(client: AsyncClient, token: str, **overrides) -> dict:
    payload = {
        "name": "Cuenta Corriente",
        "bank": "OpenBank",
        "account_type": "checking",
        "currency": "EUR",
        "balance": "1000.00",
        **overrides,
    }
    resp = await client.post(
        "/api/v1/accounts", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    return resp


# ── POST /accounts ─────────────────────────────────────────────────────────────

async def test_create_account_success(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await _create_account(client, token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Cuenta Corriente"
    assert data["bank"] == "OpenBank"
    assert data["account_type"] == "checking"
    assert data["currency"] == "EUR"
    assert data["is_active"] is True


async def test_create_account_invalid_type(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/accounts",
        json={"name": "X", "bank": "Y", "account_type": "invalid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_create_account_no_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/accounts",
        json={"name": "X", "bank": "Y", "account_type": "checking"},
    )
    assert resp.status_code == 401


# ── GET /accounts ──────────────────────────────────────────────────────────────

async def test_list_accounts_empty(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_accounts(client: AsyncClient):
    token = await _register_and_token(client)
    await _create_account(client, token, name="Cuenta 1")
    await _create_account(client, token, name="Cuenta 2")
    resp = await client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── GET /accounts/{id} ─────────────────────────────────────────────────────────

async def test_get_account(client: AsyncClient):
    token = await _register_and_token(client)
    created = (await _create_account(client, token)).json()
    resp = await client.get(
        f"/api/v1/accounts/{created['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_account_not_found(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.get(
        "/api/v1/accounts/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_account_other_user(client: AsyncClient):
    token_a = await _register_and_token(client, "a@example.com")
    token_b = await _register_and_token(client, "b@example.com")
    account = (await _create_account(client, token_a)).json()
    resp = await client.get(
        f"/api/v1/accounts/{account['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404


# ── PATCH /accounts/{id} ───────────────────────────────────────────────────────

async def test_update_account(client: AsyncClient):
    token = await _register_and_token(client)
    account = (await _create_account(client, token)).json()
    resp = await client.patch(
        f"/api/v1/accounts/{account['id']}",
        json={"name": "Cuenta Actualizada", "is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Cuenta Actualizada"
    assert data["is_active"] is False
    assert data["bank"] == "OpenBank"  # unchanged


async def test_update_account_partial(client: AsyncClient):
    token = await _register_and_token(client)
    account = (await _create_account(client, token, balance="500.00")).json()
    resp = await client.patch(
        f"/api/v1/accounts/{account['id']}",
        json={"balance": "750.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["balance"] == "750.00"


# ── DELETE /accounts/{id} ──────────────────────────────────────────────────────

async def test_delete_account(client: AsyncClient):
    token = await _register_and_token(client)
    account = (await _create_account(client, token)).json()
    resp = await client.delete(
        f"/api/v1/accounts/{account['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 204
    # Verify gone
    get_resp = await client.get(
        f"/api/v1/accounts/{account['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.status_code == 404


async def test_delete_account_not_found(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.delete(
        "/api/v1/accounts/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_transactions_deleted_with_account(client: AsyncClient):
    """Deleting an account must cascade-delete its transactions."""
    token = await _register_and_token(client, "cascade@example.com")
    account = (await _create_account(client, token)).json()
    # Create a transaction
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "-50.00",
            "description": "Test",
            "transaction_type": "expense",
            "date": "2026-03-01",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # Delete account
    await client.delete(
        f"/api/v1/accounts/{account['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    # Transactions list should be empty
    resp = await client.get(
        "/api/v1/transactions", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
