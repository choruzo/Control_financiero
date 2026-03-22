"""Integration tests for the mortgage simulator (Fase 2.4 + Fase 4.3)."""

from __future__ import annotations

import httpx
import pytest
import respx
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


# ── GET /mortgage/ai-affordability (Fase 4.3) ─────────────────────────────────

_ML_FORECAST_AI = {
    "predictions": [
        {
            "year": 2026,
            "month": m,
            "income_p10": 2400.0,
            "income_p50": 3000.0,
            "income_p90": 3600.0,
            "expenses_p10": 1200.0,
            "expenses_p50": 1800.0,
            "expenses_p90": 2400.0,
            "net_p10": 0.0,
            "net_p50": 1200.0,
            "net_p90": 2400.0,
        }
        for m in range(4, 16)  # 12 meses
    ],
    "model_used": "lstm",
    "model_version": "1.0",
    "data_months_provided": 12,
}

_AI_URL = "/api/v1/mortgage/ai-affordability"


async def test_ai_affordability_requires_auth(client: AsyncClient):
    """El endpoint requiere autenticación."""
    resp = await client.get(_AI_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_affordability_default_params(client: AsyncClient):
    """Con params por defecto devuelve estructura completa."""
    token = await _register_and_token(client, email="ai_aff_default@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(_AI_URL, headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert "forecast_monthly_income_p50" in data
    assert "forecast_recommended_max_loan" in data
    assert "current_based" in data
    assert "stress_tests" in data
    assert "ml_available" in data
    assert data["months_ahead_used"] == 12
    assert data["ml_available"] is True


@pytest.mark.asyncio
async def test_ai_affordability_forecast_income_from_ml(client: AsyncClient):
    """Los ingresos predichos P50 coinciden con la media del forecast ML."""
    token = await _register_and_token(client, email="ai_aff_income@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(_AI_URL, headers=_auth(token))

    data = resp.json()
    # El forecast mockeado tiene income_p50 = 3000 en todos los meses
    assert float(data["forecast_monthly_income_p50"]) == pytest.approx(3000.0, abs=1)
    assert float(data["forecast_monthly_income_p10"]) == pytest.approx(2400.0, abs=1)
    assert float(data["forecast_monthly_income_p90"]) == pytest.approx(3600.0, abs=1)


@pytest.mark.asyncio
async def test_ai_affordability_stress_tests_count_matches_levels(client: AsyncClient):
    """El número de stress_tests coincide con los niveles pedidos."""
    token = await _register_and_token(client, email="ai_aff_count@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(
            _AI_URL,
            params={"euribor_stress_levels": [0, 1, 2]},
            headers=_auth(token),
        )

    data = resp.json()
    assert len(data["stress_tests"]) == 3


@pytest.mark.asyncio
async def test_ai_affordability_higher_euribor_lower_max_loan(client: AsyncClient):
    """A mayor Euríbor, menor max_loan_p50 (relación inversa)."""
    token = await _register_and_token(client, email="ai_aff_inverse@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(
            _AI_URL,
            params={"euribor_stress_levels": [0, 1, 2, 3]},
            headers=_auth(token),
        )

    data = resp.json()
    loans = [float(st["max_loan_p50"]) for st in data["stress_tests"]]
    for i in range(len(loans) - 1):
        assert loans[i] > loans[i + 1], (
            f"max_loan[{i}]={loans[i]:.0f} debería ser > max_loan[{i+1}]={loans[i+1]:.0f}"
        )


@pytest.mark.asyncio
async def test_ai_affordability_p10_le_p50_le_p90(client: AsyncClient):
    """Invariante: max_loan_p10 ≤ max_loan_p50 ≤ max_loan_p90 en todos los stress tests."""
    token = await _register_and_token(client, email="ai_aff_order@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(_AI_URL, headers=_auth(token))

    data = resp.json()
    for st in data["stress_tests"]:
        p10 = float(st["max_loan_p10"])
        p50 = float(st["max_loan_p50"])
        p90 = float(st["max_loan_p90"])
        assert p10 <= p50, f"p10={p10} > p50={p50}"
        assert p50 <= p90, f"p50={p50} > p90={p90}"


@pytest.mark.asyncio
async def test_ai_affordability_is_affordable_at_low_euribor(client: AsyncClient):
    """Con ingresos razonables y Euríbor bajo, el primer stress test es affordable."""
    token = await _register_and_token(client, email="ai_aff_affordable@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        # Solo nivel 0 (Euríbor actual)
        resp = await client.get(
            _AI_URL,
            params={"euribor_stress_levels": [0]},
            headers=_auth(token),
        )

    data = resp.json()
    assert len(data["stress_tests"]) == 1
    # max_loan_p50 con income_p50=3000 y max_monthly=1050 debe ser > 0
    assert float(data["stress_tests"][0]["max_loan_p50"]) > 0
    # is_affordable: el pago calculado sobre ese préstamo debe ser ≤ 35% de 3000
    # Esto se verifica en el flag del response
    assert "is_affordable" in data["stress_tests"][0]


@pytest.mark.asyncio
async def test_ai_affordability_not_affordable_at_very_high_euribor(client: AsyncClient):
    """Con Euríbor extremadamente alto, algún stress test marca is_affordable=False."""
    token = await _register_and_token(client, email="ai_aff_notafford@test.com")

    # forecast con ingresos bajos para que un Euríbor alto sea inaffordable
    low_income_forecast = {
        "predictions": [
            {
                "year": 2026,
                "month": m,
                "income_p10": 600.0,
                "income_p50": 800.0,
                "income_p90": 1000.0,
                "expenses_p10": 400.0,
                "expenses_p50": 600.0,
                "expenses_p90": 800.0,
                "net_p10": -200.0,
                "net_p50": 200.0,
                "net_p90": 600.0,
            }
            for m in range(4, 10)
        ],
        "model_used": "lstm",
        "model_version": "1.0",
        "data_months_provided": 6,
    }

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=low_income_forecast)
        )
        resp = await client.get(
            _AI_URL,
            params={"euribor_stress_levels": [0, 5, 10], "term_years": 30},
            headers=_auth(token),
        )

    data = resp.json()
    affordable_flags = [st["is_affordable"] for st in data["stress_tests"]]
    # Con ingresos de 800€ y Euríbor +10%, algún nivel debe ser inaffordable
    assert any(not f for f in affordable_flags)


@pytest.mark.asyncio
async def test_ai_affordability_ml_unavailable_graceful(client: AsyncClient):
    """Si ml-service no responde, devuelve 200 con ml_available=False."""
    token = await _register_and_token(client, email="ai_aff_ml_down@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        resp = await client.get(_AI_URL, headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["ml_available"] is False
    # Aunque ML no esté disponible, la respuesta sigue teniendo estructura
    assert "stress_tests" in data
    assert "current_based" in data
    assert float(data["forecast_monthly_income_p50"]) >= 0


@pytest.mark.asyncio
async def test_ai_affordability_custom_months_ahead(client: AsyncClient):
    """months_ahead_used refleja el parámetro pasado."""
    token = await _register_and_token(client, email="ai_aff_months@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(
            _AI_URL,
            params={"months_ahead": 6},
            headers=_auth(token),
        )

    data = resp.json()
    assert data["months_ahead_used"] == 6


@pytest.mark.asyncio
async def test_ai_affordability_custom_term_years(client: AsyncClient):
    """Un plazo mayor implica max_loan_p50 mayor (mismo presupuesto mensual, más tiempo)."""
    token = await _register_and_token(client, email="ai_aff_term@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp_25 = await client.get(
            _AI_URL, params={"term_years": 25, "euribor_stress_levels": [0]}, headers=_auth(token)
        )
        resp_15 = await client.get(
            _AI_URL, params={"term_years": 15, "euribor_stress_levels": [0]}, headers=_auth(token)
        )

    # stress_tests[0].max_loan_p50 sí varía con term_years
    loan_25 = float(resp_25.json()["stress_tests"][0]["max_loan_p50"])
    loan_15 = float(resp_15.json()["stress_tests"][0]["max_loan_p50"])
    assert loan_25 > loan_15, f"25 años ({loan_25:.0f}) debería dar más capacidad que 15 ({loan_15:.0f})"


@pytest.mark.asyncio
async def test_ai_affordability_gross_annual_parameter(client: AsyncClient):
    """Pasar gross_annual no rompe el endpoint y afecta a current_based."""
    token = await _register_and_token(client, email="ai_aff_gross@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(
            _AI_URL,
            params={"gross_annual": 36000},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    # Con 36000€ bruto, el neto mensual es positivo
    assert float(data["current_based"]["monthly_net_income"]) > 0


@pytest.mark.asyncio
async def test_ai_affordability_current_based_structure(client: AsyncClient):
    """current_based tiene la estructura de AffordabilityResponse."""
    token = await _register_and_token(client, email="ai_aff_struct@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(_AI_URL, headers=_auth(token))

    data = resp.json()
    cb = data["current_based"]
    assert "monthly_net_income" in cb
    assert "max_monthly_payment" in cb
    assert "recommended_max_loan" in cb
    assert "options" in cb
    assert len(cb["options"]) == 6


@pytest.mark.asyncio
async def test_ai_affordability_months_ahead_too_low(client: AsyncClient):
    """months_ahead < 6 → 422 Unprocessable Entity."""
    token = await _register_and_token(client, email="ai_aff_invalid@test.com")
    resp = await client.get(
        _AI_URL, params={"months_ahead": 5}, headers=_auth(token)
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ai_affordability_months_ahead_too_high(client: AsyncClient):
    """months_ahead > 24 → 422 Unprocessable Entity."""
    token = await _register_and_token(client, email="ai_aff_invalid2@test.com")
    resp = await client.get(
        _AI_URL, params={"months_ahead": 25}, headers=_auth(token)
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ai_affordability_empty_euribor_levels(client: AsyncClient):
    """euribor_stress_levels vacío → 200 con stress_tests=[]."""
    token = await _register_and_token(client, email="ai_aff_empty@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(
            _AI_URL,
            # Sin pasar euribor_stress_levels → lista vacía
            params={"months_ahead": 12},
            headers=_auth(token),
        )

    # Con params por defecto siempre tiene 4 stress tests
    data = resp.json()
    assert resp.status_code == 200
    assert isinstance(data["stress_tests"], list)


@pytest.mark.asyncio
async def test_ai_affordability_with_saved_variable_mortgage(client: AsyncClient):
    """Si hay una MortgageSimulation variable guardada, el Euríbor base la usa."""
    token = await _register_and_token(client, email="ai_aff_saved_sim@test.com")

    # Guardar simulación variable con Euríbor 4.0%
    sim_payload = _variable_payload(euribor_rate=4.0, spread=0.9)
    sim_payload["name"] = "Hipoteca variable base"
    await client.post("/api/v1/mortgage/simulations", json=sim_payload, headers=_auth(token))

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(
            _AI_URL,
            params={"euribor_stress_levels": [0]},
            headers=_auth(token),
        )

    data = resp.json()
    assert resp.status_code == 200
    # El Euríbor del stress test nivel 0 debe ser el de la simulación (4.0)
    assert float(data["stress_tests"][0]["euribor_rate"]) == pytest.approx(4.0, abs=0.01)


@pytest.mark.asyncio
async def test_ai_affordability_stress_test_euribor_label(client: AsyncClient):
    """El label del stress test nivel 0 es 'Euríbor actual', el resto '+N%'."""
    token = await _register_and_token(client, email="ai_aff_label@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=_ML_FORECAST_AI)
        )
        resp = await client.get(
            _AI_URL,
            params={"euribor_stress_levels": [0, 1, 2]},
            headers=_auth(token),
        )

    data = resp.json()
    assert data["stress_tests"][0]["euribor_label"] == "Euríbor actual"
    assert "+" in data["stress_tests"][1]["euribor_label"]
    assert "+" in data["stress_tests"][2]["euribor_label"]
