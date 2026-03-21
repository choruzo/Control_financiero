import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_and_token(client: AsyncClient, email: str = "invest@example.com") -> str:
    reg = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "securepass"}
    )
    return reg.json()["access_token"]


async def _create_account(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/api/v1/accounts",
        json={"name": "Cuenta Inversión", "bank": "Banco", "account_type": "investment"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _create_deposit(
    client: AsyncClient, token: str, **overrides: object
) -> object:
    payload = {
        "name": "Depósito a plazo fijo",
        "investment_type": "deposit",
        "principal_amount": "10000.00",
        "interest_rate": "4.2500",
        "interest_type": "simple",
        "start_date": "2026-01-01",
        "maturity_date": "2026-12-31",
        "renewal_period_months": 12,
        **overrides,
    }
    return await client.post(
        "/api/v1/investments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


# ── POST /investments ─────────────────────────────────────────────────────────


async def test_create_deposit_success(client: AsyncClient):
    token = await _register_and_token(client, "cd_ok@example.com")
    resp = await _create_deposit(client, token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Depósito a plazo fijo"
    assert data["investment_type"] == "deposit"
    assert data["interest_type"] == "simple"
    assert data["compounding_frequency"] is None
    assert data["renewals_count"] == 0
    assert data["is_active"] is True


async def test_create_investment_with_account(client: AsyncClient):
    token = await _register_and_token(client, "cd_acc@example.com")
    account = await _create_account(client, token)
    resp = await _create_deposit(client, token, account_id=account["id"])
    assert resp.status_code == 201
    assert resp.json()["account_id"] == account["id"]


async def test_create_investment_invalid_account(client: AsyncClient):
    token = await _register_and_token(client, "cd_bad_acc@example.com")
    resp = await _create_deposit(
        client, token, account_id="00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


async def test_create_compound_investment_success(client: AsyncClient):
    token = await _register_and_token(client, "cd_comp@example.com")
    resp = await _create_deposit(
        client,
        token,
        investment_type="fund",
        interest_type="compound",
        compounding_frequency="monthly",
    )
    assert resp.status_code == 201
    assert resp.json()["compounding_frequency"] == "monthly"


async def test_create_compound_missing_frequency_fails(client: AsyncClient):
    token = await _register_and_token(client, "cd_miss@example.com")
    resp = await _create_deposit(
        client,
        token,
        interest_type="compound",
        # compounding_frequency intentionally omitted
    )
    assert resp.status_code == 422


async def test_create_simple_with_frequency_fails(client: AsyncClient):
    token = await _register_and_token(client, "cd_sf@example.com")
    resp = await _create_deposit(
        client,
        token,
        interest_type="simple",
        compounding_frequency="monthly",
    )
    assert resp.status_code == 422


async def test_create_maturity_before_start_fails(client: AsyncClient):
    token = await _register_and_token(client, "cd_mat@example.com")
    resp = await _create_deposit(
        client,
        token,
        start_date="2026-12-31",
        maturity_date="2026-01-01",
    )
    assert resp.status_code == 422


# ── GET /investments ──────────────────────────────────────────────────────────


async def test_list_investments_empty(client: AsyncClient):
    token = await _register_and_token(client, "li_empty@example.com")
    resp = await client.get(
        "/api/v1/investments", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_investments_filter_by_type(client: AsyncClient):
    token = await _register_and_token(client, "li_type@example.com")
    await _create_deposit(client, token, investment_type="deposit")
    await _create_deposit(client, token, investment_type="fund", name="Fondo A",
                          interest_type="compound", compounding_frequency="annually")

    resp_dep = await client.get(
        "/api/v1/investments?investment_type=deposit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_dep.status_code == 200
    assert all(i["investment_type"] == "deposit" for i in resp_dep.json())
    assert len(resp_dep.json()) == 1

    resp_fund = await client.get(
        "/api/v1/investments?investment_type=fund",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(resp_fund.json()) == 1


async def test_list_investments_filter_by_active(client: AsyncClient):
    token = await _register_and_token(client, "li_active@example.com")
    create_resp = await _create_deposit(client, token)
    inv_id = create_resp.json()["id"]

    # Deactivate it
    await client.patch(
        f"/api/v1/investments/{inv_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp_active = await client.get(
        "/api/v1/investments?is_active=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_active.json() == []

    resp_inactive = await client.get(
        "/api/v1/investments?is_active=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(resp_inactive.json()) == 1


# ── GET /investments/{id} ─────────────────────────────────────────────────────


async def test_get_investment_not_found(client: AsyncClient):
    token = await _register_and_token(client, "gi_nf@example.com")
    resp = await client.get(
        "/api/v1/investments/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_investment_other_user_returns_404(client: AsyncClient):
    token_a = await _register_and_token(client, "gi_a@example.com")
    token_b = await _register_and_token(client, "gi_b@example.com")
    create_resp = await _create_deposit(client, token_a)
    inv_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/investments/{inv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ── GET /investments/{id}/status ──────────────────────────────────────────────


async def test_get_investment_status_simple_interest(client: AsyncClient):
    token = await _register_and_token(client, "st_simple@example.com")
    # Start date well in the past to guarantee positive days_held
    resp = await _create_deposit(
        client,
        token,
        principal_amount="10000.00",
        interest_rate="4.2500",
        interest_type="simple",
        start_date="2026-01-01",
        maturity_date="2026-12-31",
    )
    inv_id = resp.json()["id"]

    status_resp = await client.get(
        f"/api/v1/investments/{inv_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert "accrued_interest" in data
    assert "total_return" in data
    assert "return_percentage" in data
    assert "days_held" in data
    assert data["days_held"] >= 0
    # For a simple interest deposit accrued_interest should be >= 0
    from decimal import Decimal
    assert Decimal(data["accrued_interest"]) >= Decimal("0")


async def test_get_investment_status_compound_interest(client: AsyncClient):
    token = await _register_and_token(client, "st_comp@example.com")
    resp = await _create_deposit(
        client,
        token,
        principal_amount="10000.00",
        interest_rate="5.0000",
        interest_type="compound",
        compounding_frequency="monthly",
        start_date="2025-01-01",
        maturity_date="2026-12-31",
    )
    inv_id = resp.json()["id"]

    status_resp = await client.get(
        f"/api/v1/investments/{inv_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == 200
    data = status_resp.json()
    from decimal import Decimal
    # Compound should yield more than simple for same rate over ~15 months
    assert Decimal(data["accrued_interest"]) > Decimal("0")
    assert data["days_to_maturity"] is not None


async def test_get_investment_status_no_maturity(client: AsyncClient):
    token = await _register_and_token(client, "st_nm@example.com")
    resp = await _create_deposit(
        client,
        token,
        maturity_date=None,
        auto_renew=False,
        renewal_period_months=None,
    )
    inv_id = resp.json()["id"]

    status_resp = await client.get(
        f"/api/v1/investments/{inv_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["days_to_maturity"] is None


# ── PATCH /investments/{id} ───────────────────────────────────────────────────


async def test_update_investment(client: AsyncClient):
    token = await _register_and_token(client, "upd@example.com")
    create_resp = await _create_deposit(client, token)
    inv_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/investments/{inv_id}",
        json={"name": "Depósito Actualizado", "interest_rate": "3.5000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Depósito Actualizado"
    assert data["interest_rate"] == "3.5000"
    # Unchanged field should remain
    assert data["investment_type"] == "deposit"


# ── DELETE /investments/{id} ──────────────────────────────────────────────────


async def test_delete_investment(client: AsyncClient):
    token = await _register_and_token(client, "del@example.com")
    create_resp = await _create_deposit(client, token)
    inv_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/investments/{inv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/investments/{inv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 404


# ── POST /investments/{id}/renew ──────────────────────────────────────────────


async def test_renew_investment_success(client: AsyncClient):
    token = await _register_and_token(client, "ren_ok@example.com")
    create_resp = await _create_deposit(
        client,
        token,
        start_date="2026-01-01",
        maturity_date="2026-06-30",
        renewal_period_months=6,
    )
    inv_id = create_resp.json()["id"]
    original_maturity = create_resp.json()["maturity_date"]

    renew_resp = await client.post(
        f"/api/v1/investments/{inv_id}/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert renew_resp.status_code == 200
    data = renew_resp.json()
    assert data["renewals_count"] == 1
    assert data["maturity_date"] != original_maturity
    # New maturity = 2026-12-30
    assert data["maturity_date"] == "2026-12-30"


async def test_renew_investment_no_maturity_date_fails(client: AsyncClient):
    token = await _register_and_token(client, "ren_nmd@example.com")
    create_resp = await _create_deposit(
        client,
        token,
        maturity_date=None,
        auto_renew=False,
        renewal_period_months=None,
    )
    inv_id = create_resp.json()["id"]

    renew_resp = await client.post(
        f"/api/v1/investments/{inv_id}/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert renew_resp.status_code == 400


async def test_renew_investment_no_renewal_period_fails(client: AsyncClient):
    token = await _register_and_token(client, "ren_nrp@example.com")
    create_resp = await _create_deposit(
        client,
        token,
        maturity_date="2026-12-31",
        auto_renew=False,
        renewal_period_months=None,
    )
    inv_id = create_resp.json()["id"]

    renew_resp = await client.post(
        f"/api/v1/investments/{inv_id}/renew",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert renew_resp.status_code == 400


# ── GET /investments/summary ──────────────────────────────────────────────────


async def test_investment_summary_empty(client: AsyncClient):
    token = await _register_and_token(client, "sum_empty@example.com")
    resp = await client.get(
        "/api/v1/investments/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_investments"] == 0
    assert data["total_principal"] == "0.00"
    assert data["total_return"] == "0.00"
    assert data["by_type"] == {}


async def test_investment_summary_aggregates(client: AsyncClient):
    token = await _register_and_token(client, "sum_agg@example.com")
    await _create_deposit(
        client, token, name="Dep1", principal_amount="5000.00", investment_type="deposit"
    )
    await _create_deposit(
        client,
        token,
        name="Fund1",
        investment_type="fund",
        interest_type="compound",
        compounding_frequency="annually",
        principal_amount="3000.00",
    )

    resp = await client.get(
        "/api/v1/investments/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_investments"] == 2
    from decimal import Decimal
    assert Decimal(data["total_principal"]) == Decimal("8000.00")
    assert data["by_type"]["deposit"] == 1
    assert data["by_type"]["fund"] == 1


# ── Auth ──────────────────────────────────────────────────────────────────────


async def test_unauthorized_access(client: AsyncClient):
    resp = await client.get("/api/v1/investments")
    assert resp.status_code == 401
