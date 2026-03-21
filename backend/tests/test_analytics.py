from datetime import date

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_and_token(client: AsyncClient, email: str = "analytics@example.com") -> str:
    reg = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "securepass"}
    )
    return reg.json()["access_token"]


async def _create_account(client: AsyncClient, token: str, balance: str = "5000.00") -> dict:
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "Cuenta Test",
            "bank": "Banco Test",
            "account_type": "checking",
            "balance": balance,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _create_transaction(
    client: AsyncClient, token: str, account_id: str, **overrides: object
) -> dict:
    today = date.today()
    payload = {
        "account_id": account_id,
        "amount": "100.00",
        "description": "Test transaction",
        "transaction_type": "income",
        "date": today.isoformat(),
        **overrides,
    }
    resp = await client.post(
        "/api/v1/transactions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── GET /analytics/overview ───────────────────────────────────────────────────


async def test_overview_empty(client: AsyncClient):
    token = await _register_and_token(client, "ov_empty@example.com")
    today = date.today()
    resp = await client.get(
        "/api/v1/analytics/overview",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_income"] == "0.00"
    assert data["total_expenses"] == "0.00"
    assert data["net_savings"] == "0.00"
    assert data["savings_rate"] == "0.00"
    assert data["total_balance"] == "0.00"
    assert data["transaction_count"] == 0


async def test_overview_with_data(client: AsyncClient):
    token = await _register_and_token(client, "ov_data@example.com")
    account = await _create_account(client, token, balance="3000.00")
    today = date.today()
    await _create_transaction(
        client, token, account["id"],
        amount="2000.00", transaction_type="income", date=today.isoformat()
    )
    await _create_transaction(
        client, token, account["id"],
        amount="500.00", transaction_type="expense", date=today.isoformat()
    )
    resp = await client.get(
        "/api/v1/analytics/overview",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["total_income"]) == 2000.00
    assert float(data["total_expenses"]) == 500.00
    assert float(data["net_savings"]) == 1500.00
    assert float(data["savings_rate"]) == 75.00
    assert float(data["total_balance"]) == 3000.00
    assert data["transaction_count"] == 2


async def test_overview_savings_rate_zero_income(client: AsyncClient):
    token = await _register_and_token(client, "ov_zero@example.com")
    account = await _create_account(client, token)
    today = date.today()
    await _create_transaction(
        client, token, account["id"],
        amount="300.00", transaction_type="expense", date=today.isoformat()
    )
    resp = await client.get(
        "/api/v1/analytics/overview",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["savings_rate"] == "0.00"
    assert float(data["net_savings"]) == -300.00


async def test_overview_default_current_month(client: AsyncClient):
    token = await _register_and_token(client, "ov_default@example.com")
    resp = await client.get("/api/v1/analytics/overview", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    today = date.today()
    assert data["year"] == today.year
    assert data["month"] == today.month


async def test_overview_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/overview")
    assert resp.status_code == 401


# ── GET /analytics/cashflow ───────────────────────────────────────────────────


async def test_cashflow_empty(client: AsyncClient):
    token = await _register_and_token(client, "cf_empty@example.com")
    resp = await client.get(
        "/api/v1/analytics/cashflow", params={"months": 3}, headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    for item in data:
        assert item["total_income"] == "0.00"
        assert item["total_expenses"] == "0.00"
        assert item["net"] == "0.00"


async def test_cashflow_with_data(client: AsyncClient):
    token = await _register_and_token(client, "cf_data@example.com")
    account = await _create_account(client, token)
    today = date.today()
    await _create_transaction(
        client, token, account["id"],
        amount="1000.00", transaction_type="income", date=today.isoformat()
    )
    await _create_transaction(
        client, token, account["id"],
        amount="400.00", transaction_type="expense", date=today.isoformat()
    )
    resp = await client.get(
        "/api/v1/analytics/cashflow", params={"months": 1}, headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert float(data[0]["total_income"]) == 1000.00
    assert float(data[0]["total_expenses"]) == 400.00
    assert float(data[0]["net"]) == 600.00


async def test_cashflow_months_validation(client: AsyncClient):
    token = await _register_and_token(client, "cf_val@example.com")
    resp = await client.get(
        "/api/v1/analytics/cashflow", params={"months": 61}, headers=_auth(token)
    )
    assert resp.status_code == 422


async def test_cashflow_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/cashflow")
    assert resp.status_code == 401


# ── GET /analytics/expenses-by-category ──────────────────────────────────────


async def test_expenses_by_category_empty(client: AsyncClient):
    token = await _register_and_token(client, "ebc_empty@example.com")
    today = date.today()
    resp = await client.get(
        "/api/v1/analytics/expenses-by-category",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_expenses_by_category_with_data(client: AsyncClient):
    token = await _register_and_token(client, "ebc_data@example.com")
    account = await _create_account(client, token)
    today = date.today()

    # Create a custom category to group expenses
    cat_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Alimentación Test", "color": "#FF0000"},
        headers=_auth(token),
    )
    category_id = cat_resp.json()["id"]

    await _create_transaction(
        client, token, account["id"],
        amount="600.00", transaction_type="expense",
        date=today.isoformat(), category_id=category_id
    )
    await _create_transaction(
        client, token, account["id"],
        amount="400.00", transaction_type="expense",
        date=today.isoformat(), category_id=category_id
    )

    resp = await client.get(
        "/api/v1/analytics/expenses-by-category",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert float(data[0]["total_amount"]) == 1000.00
    assert data[0]["transaction_count"] == 2
    assert data[0]["percentage"] == "100.00"
    assert data[0]["category_name"] == "Alimentación Test"


async def test_expenses_no_category(client: AsyncClient):
    token = await _register_and_token(client, "ebc_nocat@example.com")
    account = await _create_account(client, token)
    today = date.today()
    await _create_transaction(
        client, token, account["id"],
        amount="250.00", transaction_type="expense", date=today.isoformat()
    )
    resp = await client.get(
        "/api/v1/analytics/expenses-by-category",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["category_id"] is None
    assert data[0]["category_name"] == "Sin categoría"


async def test_expenses_by_category_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/expenses-by-category")
    assert resp.status_code == 401


# ── GET /analytics/savings-rate ──────────────────────────────────────────────


async def test_savings_rate_empty(client: AsyncClient):
    token = await _register_and_token(client, "sr_empty@example.com")
    resp = await client.get(
        "/api/v1/analytics/savings-rate", params={"months": 3}, headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    for item in data:
        assert item["savings_rate"] == "0.00"
        assert item["income"] == "0.00"


async def test_savings_rate_with_data(client: AsyncClient):
    token = await _register_and_token(client, "sr_data@example.com")
    account = await _create_account(client, token)
    today = date.today()
    await _create_transaction(
        client, token, account["id"],
        amount="1000.00", transaction_type="income", date=today.isoformat()
    )
    await _create_transaction(
        client, token, account["id"],
        amount="200.00", transaction_type="expense", date=today.isoformat()
    )
    resp = await client.get(
        "/api/v1/analytics/savings-rate", params={"months": 1}, headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert float(data[0]["savings_rate"]) == 80.00
    assert float(data[0]["net_savings"]) == 800.00


async def test_savings_rate_moving_avg_available_after_3_months(client: AsyncClient):
    token = await _register_and_token(client, "sr_avg@example.com")
    resp = await client.get(
        "/api/v1/analytics/savings-rate", params={"months": 6}, headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6
    # First 2 months: no moving averages
    assert data[0]["moving_avg_3m"] is None
    assert data[1]["moving_avg_3m"] is None
    # From 3rd month: moving_avg_3m is available
    assert data[2]["moving_avg_3m"] is not None
    # First 5 months: no 6m avg
    assert data[4]["moving_avg_6m"] is None
    # 6th month: 6m avg available
    assert data[5]["moving_avg_6m"] is not None


async def test_savings_rate_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/savings-rate")
    assert resp.status_code == 401


# ── GET /analytics/trends ─────────────────────────────────────────────────────


async def test_trends_empty(client: AsyncClient):
    token = await _register_and_token(client, "tr_empty@example.com")
    today = date.today()
    resp = await client.get(
        "/api/v1/analytics/trends",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["income"] == "0.00"
    assert data["expenses"] == "0.00"
    # No previous data: all change percentages are None
    assert data["income_change_pct"] is None
    assert data["expenses_change_pct"] is None
    assert data["savings_change_pct"] is None
    assert data["income_vs_avg_pct"] is None
    assert data["expenses_vs_avg_pct"] is None
    assert data["savings_vs_avg_pct"] is None


async def test_trends_with_data(client: AsyncClient):
    token = await _register_and_token(client, "tr_data@example.com")
    account = await _create_account(client, token)
    today = date.today()
    await _create_transaction(
        client, token, account["id"],
        amount="1000.00", transaction_type="income", date=today.isoformat()
    )
    await _create_transaction(
        client, token, account["id"],
        amount="300.00", transaction_type="expense", date=today.isoformat()
    )
    resp = await client.get(
        "/api/v1/analytics/trends",
        params={"year": today.year, "month": today.month},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["income"]) == 1000.00
    assert float(data["expenses"]) == 300.00
    assert float(data["net_savings"]) == 700.00
    assert data["year"] == today.year
    assert data["month"] == today.month


async def test_trends_default_current_month(client: AsyncClient):
    token = await _register_and_token(client, "tr_default@example.com")
    resp = await client.get("/api/v1/analytics/trends", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    today = date.today()
    assert data["year"] == today.year
    assert data["month"] == today.month


async def test_trends_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/trends")
    assert resp.status_code == 401
