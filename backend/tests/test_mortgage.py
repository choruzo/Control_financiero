"""Integration tests for the mortgage simulator (Fase 2.4)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_and_token(client: AsyncClient, email: str = "mortgage@test.com") -> str:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Secret123!"}
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _fixed_payload(**overrides) -> dict:
    base = {
        "property_price": 250000,
        "down_payment": 50000,
        "rate_type": "fixed",
        "term_years": 25,
        "interest_rate": 3.5,
        "include_costs": True,
        "property_type": "second_hand",
    }
    base.update(overrides)
    return base


def _variable_payload(**overrides) -> dict:
    base = {
        "property_price": 250000,
        "down_payment": 50000,
        "rate_type": "variable",
        "term_years": 25,
        "euribor_rate": 3.5,
        "spread": 0.8,
        "review_frequency": "annual",
        "include_costs": True,
        "property_type": "second_hand",
    }
    base.update(overrides)
    return base


def _mixed_payload(**overrides) -> dict:
    base = {
        "property_price": 250000,
        "down_payment": 50000,
        "rate_type": "mixed",
        "term_years": 25,
        "interest_rate": 2.9,
        "euribor_rate": 3.5,
        "spread": 0.8,
        "fixed_years": 5,
        "review_frequency": "annual",
        "include_costs": True,
        "property_type": "second_hand",
    }
    base.update(overrides)
    return base


# ── POST /mortgage/simulate — fixed ───────────────────────────────────────────


async def test_simulate_fixed_success(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post("/api/v1/mortgage/simulate", json=_fixed_payload(), headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["rate_type"] == "fixed"
    assert data["term_years"] == 25
    assert float(data["loan_amount"]) == pytest.approx(200000, abs=1)


async def test_simulate_fixed_monthly_payment(client: AsyncClient):
    """PMT for 200k @ 3.5% / 25y ≈ 1001 €."""
    token = await _register_and_token(client)
    resp = await client.post("/api/v1/mortgage/simulate", json=_fixed_payload(), headers=_auth(token))

    data = resp.json()
    pmt = float(data["initial_monthly_payment"])
    # PMT = 200000 * 0.035/12 * (1+0.035/12)^300 / ((1+0.035/12)^300 - 1) ≈ 1001
    assert 990 <= pmt <= 1015


async def test_simulate_fixed_schedule_length(client: AsyncClient):
    """Schedule must have exactly term_years * 12 rows."""
    token = await _register_and_token(client)
    resp = await client.post("/api/v1/mortgage/simulate", json=_fixed_payload(), headers=_auth(token))

    data = resp.json()
    assert len(data["schedule"]) == 25 * 12


async def test_simulate_fixed_with_closing_costs(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate",
        json=_fixed_payload(include_costs=True, property_type="second_hand"),
        headers=_auth(token),
    )

    data = resp.json()
    costs = data["closing_costs"]
    assert costs is not None
    # ITP default 8% of 250000 = 20000
    assert float(costs["tax"]) == pytest.approx(20000, abs=1)
    # Notary 0.5% of 250000 = 1250
    assert float(costs["notary"]) == pytest.approx(1250, abs=1)


async def test_simulate_fixed_no_costs(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate",
        json=_fixed_payload(include_costs=False),
        headers=_auth(token),
    )

    data = resp.json()
    assert data["closing_costs"] is None


# ── POST /mortgage/simulate — variable ────────────────────────────────────────


async def test_simulate_variable_annual_review(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate",
        json=_variable_payload(review_frequency="annual"),
        headers=_auth(token),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["rate_type"] == "variable"
    # Variable rate = euribor + spread = 3.5 + 0.8 = 4.3%, applied_rate consistent
    first_row = data["schedule"][0]
    assert float(first_row["applied_rate"]) == pytest.approx(4.3, abs=0.01)


async def test_simulate_variable_semiannual_review(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate",
        json=_variable_payload(review_frequency="semiannual"),
        headers=_auth(token),
    )

    assert resp.status_code == 200
    assert len(resp.json()["schedule"]) == 25 * 12


# ── POST /mortgage/simulate — mixed ───────────────────────────────────────────


async def test_simulate_mixed_success(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate", json=_mixed_payload(), headers=_auth(token)
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["rate_type"] == "mixed"
    # First 5 years (60 months) should have fixed rate applied
    for row in data["schedule"][:60]:
        assert float(row["applied_rate"]) == pytest.approx(2.9, abs=0.01)
    # After fixed period, variable rate kicks in
    assert float(data["schedule"][60]["applied_rate"]) == pytest.approx(4.3, abs=0.01)


async def test_simulate_mixed_fixed_years_ge_term_fails(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate",
        json=_mixed_payload(fixed_years=25),  # equals term_years → invalid
        headers=_auth(token),
    )
    assert resp.status_code == 422


# ── POST /mortgage/simulate — validation ──────────────────────────────────────


async def test_simulate_fixed_missing_interest_rate(client: AsyncClient):
    token = await _register_and_token(client)
    payload = _fixed_payload()
    del payload["interest_rate"]
    resp = await client.post("/api/v1/mortgage/simulate", json=payload, headers=_auth(token))
    assert resp.status_code == 422


async def test_simulate_variable_missing_euribor(client: AsyncClient):
    token = await _register_and_token(client)
    payload = _variable_payload()
    del payload["euribor_rate"]
    resp = await client.post("/api/v1/mortgage/simulate", json=payload, headers=_auth(token))
    assert resp.status_code == 422


async def test_simulate_down_payment_exceeds_price(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate",
        json=_fixed_payload(down_payment=300000),  # > property_price
        headers=_auth(token),
    )
    assert resp.status_code == 422


async def test_simulate_term_out_of_range(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/mortgage/simulate",
        json=_fixed_payload(term_years=50),
        headers=_auth(token),
    )
    assert resp.status_code == 422


# ── POST /mortgage/compare ────────────────────────────────────────────────────


async def test_compare_two_scenarios(client: AsyncClient):
    token = await _register_and_token(client)
    payload = {
        "property_price": 250000,
        "down_payment": 50000,
        "term_years": 25,
        "scenarios": [
            {"name": "Fijo 3.5%", "rate_type": "fixed", "interest_rate": 3.5},
            {
                "name": "Variable Eur+spread",
                "rate_type": "variable",
                "euribor_rate": 3.5,
                "spread": 0.8,
            },
        ],
    }
    resp = await client.post("/api/v1/mortgage/compare", json=payload, headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert float(data["loan_amount"]) == pytest.approx(200000, abs=1)
    assert len(data["scenarios"]) == 2
    # First scenario has no savings_vs_first (it IS the reference)
    assert data["scenarios"][0]["savings_vs_first"] is None


async def test_compare_savings_vs_first_sign(client: AsyncClient):
    """A lower-rate scenario should show positive savings vs a higher-rate reference."""
    token = await _register_and_token(client)
    payload = {
        "property_price": 200000,
        "down_payment": 40000,
        "term_years": 20,
        "scenarios": [
            {"name": "Caro", "rate_type": "fixed", "interest_rate": 5.0},
            {"name": "Barato", "rate_type": "fixed", "interest_rate": 2.5},
        ],
    }
    resp = await client.post("/api/v1/mortgage/compare", json=payload, headers=_auth(token))
    data = resp.json()
    savings = float(data["scenarios"][1]["savings_vs_first"])
    assert savings > 0


# ── GET /mortgage/affordability ───────────────────────────────────────────────


async def test_affordability_no_income(client: AsyncClient):
    """User with no transactions → all amounts should be 0."""
    token = await _register_and_token(client)
    resp = await client.get("/api/v1/mortgage/affordability", headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert float(data["monthly_net_income"]) == pytest.approx(0, abs=0.01)
    assert float(data["max_monthly_payment"]) == pytest.approx(0, abs=0.01)


async def test_affordability_with_income(client: AsyncClient):
    """User with income transactions → affordability > 0."""
    token = await _register_and_token(client, email="afford@test.com")

    # Create account
    acc_resp = await client.post(
        "/api/v1/accounts",
        json={"name": "Cuenta", "bank": "Banco", "account_type": "checking"},
        headers=_auth(token),
    )
    account_id = acc_resp.json()["id"]

    # Add income transactions for last 3 months
    for month in [1, 2, 3]:
        await client.post(
            "/api/v1/transactions",
            json={
                "account_id": account_id,
                "amount": 3000,
                "transaction_type": "income",
                "description": "Salary",
                "date": f"2026-0{month}-15",
            },
            headers=_auth(token),
        )

    resp = await client.get("/api/v1/mortgage/affordability", headers=_auth(token))
    data = resp.json()

    assert float(data["monthly_net_income"]) == pytest.approx(3000, abs=1)
    assert float(data["max_monthly_payment"]) == pytest.approx(1050, abs=1)
    assert float(data["recommended_max_loan"]) > 0
    assert len(data["options"]) == 6


# ── POST /mortgage/simulations ────────────────────────────────────────────────


async def test_save_simulation_success(client: AsyncClient):
    token = await _register_and_token(client)
    payload = _fixed_payload()
    payload["name"] = "Mi hipoteca fija"

    resp = await client.post("/api/v1/mortgage/simulations", json=payload, headers=_auth(token))

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Mi hipoteca fija"
    assert data["rate_type"] == "fixed"
    assert "id" in data


async def test_save_simulation_calculated_fields(client: AsyncClient):
    """Saved simulation must store pre-calculated payment and totals."""
    token = await _register_and_token(client)
    payload = _fixed_payload()
    payload["name"] = "Test cálculo"

    resp = await client.post("/api/v1/mortgage/simulations", json=payload, headers=_auth(token))
    data = resp.json()

    pmt = float(data["initial_monthly_payment"])
    total = float(data["total_amount_paid"])
    interest = float(data["total_interest"])

    assert 990 <= pmt <= 1015
    assert total == pytest.approx(pmt * 300, abs=50)
    assert interest == pytest.approx(total - 200000, abs=10)


# ── GET /mortgage/simulations ─────────────────────────────────────────────────


async def test_list_simulations(client: AsyncClient):
    token = await _register_and_token(client)

    payload_a = _fixed_payload()
    payload_a["name"] = "Simulación A"
    payload_b = _variable_payload()
    payload_b["name"] = "Simulación B"

    await client.post("/api/v1/mortgage/simulations", json=payload_a, headers=_auth(token))
    await client.post("/api/v1/mortgage/simulations", json=payload_b, headers=_auth(token))

    resp = await client.get("/api/v1/mortgage/simulations", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_list_simulations_user_isolation(client: AsyncClient):
    token_a = await _register_and_token(client, email="user_a@test.com")
    token_b = await _register_and_token(client, email="user_b@test.com")

    payload = _fixed_payload()
    payload["name"] = "Solo mía"
    await client.post("/api/v1/mortgage/simulations", json=payload, headers=_auth(token_a))

    resp = await client.get("/api/v1/mortgage/simulations", headers=_auth(token_b))
    assert resp.json() == []


# ── GET /mortgage/simulations/{id} ────────────────────────────────────────────


async def test_get_simulation_success(client: AsyncClient):
    token = await _register_and_token(client)
    payload = _fixed_payload()
    payload["name"] = "Get me"

    created = (
        await client.post("/api/v1/mortgage/simulations", json=payload, headers=_auth(token))
    ).json()
    sim_id = created["id"]

    resp = await client.get(f"/api/v1/mortgage/simulations/{sim_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == sim_id


async def test_get_simulation_not_found(client: AsyncClient):
    token = await _register_and_token(client)
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = await client.get(f"/api/v1/mortgage/simulations/{fake_id}", headers=_auth(token))
    assert resp.status_code == 404


# ── DELETE /mortgage/simulations/{id} ─────────────────────────────────────────


async def test_delete_simulation(client: AsyncClient):
    token = await _register_and_token(client)
    payload = _fixed_payload()
    payload["name"] = "Delete me"

    sim_id = (
        await client.post("/api/v1/mortgage/simulations", json=payload, headers=_auth(token))
    ).json()["id"]

    del_resp = await client.delete(
        f"/api/v1/mortgage/simulations/{sim_id}", headers=_auth(token)
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/mortgage/simulations/{sim_id}", headers=_auth(token)
    )
    assert get_resp.status_code == 404


# ── Authentication ────────────────────────────────────────────────────────────


async def test_simulate_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/mortgage/simulate", json=_fixed_payload())
    assert resp.status_code == 401


async def test_simulations_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/mortgage/simulations")
    assert resp.status_code == 401
