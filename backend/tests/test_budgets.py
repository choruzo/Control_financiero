import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_and_token(client: AsyncClient, email: str = "budget@example.com") -> str:
    reg = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "securepass"}
    )
    return reg.json()["access_token"]


async def _create_account(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/api/v1/accounts",
        json={"name": "Cuenta Test", "bank": "Banco", "account_type": "checking"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _create_category(
    client: AsyncClient, token: str, name: str = "Alimentación"
) -> str:
    resp = await client.post(
        "/api/v1/categories",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


async def _create_budget(
    client: AsyncClient, token: str, category_id: str, **overrides
) -> object:
    payload = {
        "category_id": category_id,
        "period_year": 2026,
        "period_month": 3,
        "limit_amount": "500.00",
        "alert_threshold": "80.00",
        **overrides,
    }
    return await client.post(
        "/api/v1/budgets",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


async def _create_expense(
    client: AsyncClient,
    token: str,
    account_id: str,
    category_id: str,
    amount: str,
) -> dict:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "amount": amount,
            "description": "Gasto test",
            "transaction_type": "expense",
            "date": "2026-03-15",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ── POST /budgets ─────────────────────────────────────────────────────────────


async def test_create_budget_success(client: AsyncClient):
    token = await _register_and_token(client, "cb_ok@example.com")
    cat_id = await _create_category(client, token)
    resp = await _create_budget(client, token, cat_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["category_id"] == cat_id
    assert data["period_year"] == 2026
    assert data["period_month"] == 3
    assert data["limit_amount"] == "500.00"
    assert data["alert_threshold"] == "80.00"


async def test_create_budget_no_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/budgets",
        json={
            "category_id": "00000000-0000-0000-0000-000000000000",
            "period_year": 2026,
            "period_month": 3,
            "limit_amount": "100.00",
        },
    )
    assert resp.status_code == 401


async def test_create_budget_duplicate_returns_409(client: AsyncClient):
    token = await _register_and_token(client, "dup@example.com")
    cat_id = await _create_category(client, token)
    resp1 = await _create_budget(client, token, cat_id)
    assert resp1.status_code == 201
    resp2 = await _create_budget(client, token, cat_id)
    assert resp2.status_code == 409


async def test_create_budget_invalid_category(client: AsyncClient):
    token = await _register_and_token(client, "inv_cat@example.com")
    resp = await _create_budget(client, token, "00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_create_budget_invalid_month(client: AsyncClient):
    token = await _register_and_token(client, "inv_month@example.com")
    cat_id = await _create_category(client, token)
    resp = await _create_budget(client, token, cat_id, period_month=13)
    assert resp.status_code == 422


# ── GET /budgets ──────────────────────────────────────────────────────────────


async def test_list_budgets_empty(client: AsyncClient):
    token = await _register_and_token(client, "list_empty@example.com")
    resp = await client.get(
        "/api/v1/budgets", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_budgets_filter_by_period(client: AsyncClient):
    token = await _register_and_token(client, "filter_period@example.com")
    cat_march = await _create_category(client, token, "Alimentación")
    cat_april = await _create_category(client, token, "Transporte")
    await _create_budget(client, token, cat_march, period_year=2026, period_month=3)
    await _create_budget(client, token, cat_april, period_year=2026, period_month=4)

    resp = await client.get(
        "/api/v1/budgets?period_year=2026&period_month=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["period_month"] == 3


# ── GET /budgets/{id} ─────────────────────────────────────────────────────────


async def test_get_budget_not_found(client: AsyncClient):
    token = await _register_and_token(client, "get_404@example.com")
    resp = await client.get(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_budget_other_user_isolation(client: AsyncClient):
    token_a = await _register_and_token(client, "iso_a@example.com")
    token_b = await _register_and_token(client, "iso_b@example.com")
    cat_id = await _create_category(client, token_a)
    budget = (await _create_budget(client, token_a, cat_id)).json()
    resp = await client.get(
        f"/api/v1/budgets/{budget['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ── PATCH /budgets/{id} ───────────────────────────────────────────────────────


async def test_update_budget_limit(client: AsyncClient):
    token = await _register_and_token(client, "upd_budget@example.com")
    cat_id = await _create_category(client, token)
    budget = (await _create_budget(client, token, cat_id)).json()
    resp = await client.patch(
        f"/api/v1/budgets/{budget['id']}",
        json={"limit_amount": "750.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["limit_amount"] == "750.00"
    assert resp.json()["alert_threshold"] == "80.00"


# ── DELETE /budgets/{id} ──────────────────────────────────────────────────────


async def test_delete_budget(client: AsyncClient):
    token = await _register_and_token(client, "del_budget@example.com")
    cat_id = await _create_category(client, token)
    budget = (await _create_budget(client, token, cat_id)).json()
    del_resp = await client.delete(
        f"/api/v1/budgets/{budget['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204
    get_resp = await client.get(
        f"/api/v1/budgets/{budget['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 404


# ── GET /budgets/{id}/status ──────────────────────────────────────────────────


async def test_budget_status_no_expenses(client: AsyncClient):
    token = await _register_and_token(client, "status_zero@example.com")
    cat_id = await _create_category(client, token)
    budget = (await _create_budget(client, token, cat_id)).json()
    resp = await client.get(
        f"/api/v1/budgets/{budget['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["spent_amount"] == "0.00"
    assert data["percentage_used"] == "0.00"
    assert data["is_over_limit"] is False
    assert data["alert_triggered"] is False


async def test_budget_status_below_threshold(client: AsyncClient):
    token = await _register_and_token(client, "below_thr@example.com")
    cat_id = await _create_category(client, token)
    account = await _create_account(client, token)
    budget = (
        await _create_budget(
            client, token, cat_id, limit_amount="500.00", alert_threshold="80.00"
        )
    ).json()
    await _create_expense(client, token, account["id"], cat_id, "-300.00")
    resp = await client.get(
        f"/api/v1/budgets/{budget['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["alert_triggered"] is False
    assert data["percentage_used"] == "60.00"


async def test_budget_status_triggers_alert(client: AsyncClient):
    token = await _register_and_token(client, "trigger_alert@example.com")
    cat_id = await _create_category(client, token)
    account = await _create_account(client, token)
    budget = (
        await _create_budget(
            client, token, cat_id, limit_amount="500.00", alert_threshold="80.00"
        )
    ).json()
    await _create_expense(client, token, account["id"], cat_id, "-450.00")
    resp = await client.get(
        f"/api/v1/budgets/{budget['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["alert_triggered"] is True
    assert data["percentage_used"] == "90.00"
    assert data["is_over_limit"] is False


async def test_budget_status_over_limit(client: AsyncClient):
    token = await _register_and_token(client, "over_limit@example.com")
    cat_id = await _create_category(client, token)
    account = await _create_account(client, token)
    budget = (
        await _create_budget(
            client, token, cat_id, limit_amount="200.00", alert_threshold="80.00"
        )
    ).json()
    await _create_expense(client, token, account["id"], cat_id, "-250.00")
    resp = await client.get(
        f"/api/v1/budgets/{budget['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["is_over_limit"] is True
    assert float(data["remaining_amount"]) < 0


async def test_budget_status_no_duplicate_alerts(client: AsyncClient):
    token = await _register_and_token(client, "no_dup_alert@example.com")
    cat_id = await _create_category(client, token)
    account = await _create_account(client, token)
    budget = (
        await _create_budget(
            client, token, cat_id, limit_amount="500.00", alert_threshold="80.00"
        )
    ).json()
    await _create_expense(client, token, account["id"], cat_id, "-450.00")
    # Primera llamada: crea la alerta
    await client.get(
        f"/api/v1/budgets/{budget['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Segunda llamada: no debe crear una segunda alerta
    await client.get(
        f"/api/v1/budgets/{budget['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    alerts_resp = await client.get(
        "/api/v1/budgets/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(alerts_resp.json()) == 1


# ── GET /budgets/status ───────────────────────────────────────────────────────


async def test_list_budget_statuses(client: AsyncClient):
    token = await _register_and_token(client, "list_statuses@example.com")
    cat1 = await _create_category(client, token, "Alimentación")
    cat2 = await _create_category(client, token, "Transporte")
    await _create_budget(client, token, cat1, period_year=2026, period_month=3)
    await _create_budget(client, token, cat2, period_year=2026, period_month=3)

    resp = await client.get(
        "/api/v1/budgets/status?period_year=2026&period_month=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for item in data:
        assert "spent_amount" in item
        assert "percentage_used" in item
        assert "alert_triggered" in item


# ── GET /budgets/alerts y PATCH /budgets/alerts/{id}/read ────────────────────


async def test_list_and_mark_alert_read(client: AsyncClient):
    token = await _register_and_token(client, "mark_read@example.com")
    cat_id = await _create_category(client, token)
    account = await _create_account(client, token)
    budget = (
        await _create_budget(
            client, token, cat_id, limit_amount="100.00", alert_threshold="80.00"
        )
    ).json()
    await _create_expense(client, token, account["id"], cat_id, "-90.00")

    # Disparar alerta consultando el status
    await client.get(
        f"/api/v1/budgets/{budget['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Listar alertas
    alerts_resp = await client.get(
        "/api/v1/budgets/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert alerts_resp.status_code == 200
    assert len(alerts_resp.json()) == 1
    alert_id = alerts_resp.json()[0]["id"]
    assert alerts_resp.json()[0]["is_read"] is False

    # Marcar como leída
    patch_resp = await client.patch(
        f"/api/v1/budgets/alerts/{alert_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_read"] is True

    # Filtrar solo no leídas: lista vacía
    unread_resp = await client.get(
        "/api/v1/budgets/alerts?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unread_resp.status_code == 200
    assert unread_resp.json() == []
