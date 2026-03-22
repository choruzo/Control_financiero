"""
Tests de integración para el motor de escenarios "what-if" (Fase 4.2).

Cubre:
- POST /api/v1/scenarios/analyze: endpoint protegido con auth
- Escenario sin modificaciones (resultado ≈ forecast base)
- Variación de sueldo (positiva y negativa)
- Añadir/eliminar gastos recurrentes
- Impacto fiscal (con y sin gross_annual)
- Variación Euríbor sin simulación hipotecaria guardada
- Degradación graceful cuando ml-service no está disponible
- Validación de parámetros
- Ordenamiento P10 ≤ P50 ≤ P90
- Campos del summary presentes
- Funciones puras de monte_carlo
"""

from __future__ import annotations

import pytest
import respx
import httpx
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_token(client: AsyncClient, email: str) -> str:
    """Registra un usuario y devuelve el access_token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


ML_FORECAST_RESPONSE = {
    "predictions": [
        {
            "year": 2026,
            "month": m,
            "income_p10": 2000.0,
            "income_p50": 2500.0,
            "income_p90": 3000.0,
            "expenses_p10": 1500.0,
            "expenses_p50": 1800.0,
            "expenses_p90": 2100.0,
            "net_p10": -100.0,
            "net_p50": 700.0,
            "net_p90": 1500.0,
        }
        for m in range(4, 10)  # 6 meses
    ],
    "model_used": "prophet",
    "model_version": "1.0",
    "data_months_provided": 3,
}


# ---------------------------------------------------------------------------
# Tests de autenticación
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_requires_auth(client):
    """El endpoint de scenarios requiere autenticación."""
    resp = await client.post("/api/v1/scenarios/analyze", json={"name": "Test"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests principales
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_no_modifications(client):
    """Sin modificaciones, el escenario devuelve respuesta válida."""
    token = await _register_and_token(client, "scenario_base@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"name": "Sin cambios", "months_ahead": 6},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Sin cambios"
    assert "monthly_results" in data
    assert "summary" in data
    assert len(data["monthly_results"]) == 6


@pytest.mark.asyncio
async def test_salary_increase_boosts_net(client):
    """Sueldo +10% → scenario_net_p50 > base_net para todos los meses."""
    token = await _register_and_token(client, "scenario_salary_up@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 3, "salary_variation_pct": "10"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for month in data["monthly_results"]:
        assert float(month["scenario_net_p50"]) > float(month["base_net"]), (
            f"P50 del escenario debería ser mayor al base: {month}"
        )


@pytest.mark.asyncio
async def test_salary_decrease_reduces_net(client):
    """Sueldo -20% → scenario_income < base_income."""
    token = await _register_and_token(client, "scenario_salary_down@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 3, "salary_variation_pct": "-20"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for month in data["monthly_results"]:
        assert float(month["scenario_income"]) < float(month["base_income"]), (
            f"Ingreso escenario debería ser menor: {month}"
        )


@pytest.mark.asyncio
async def test_add_recurring_expense(client):
    """Añadir gasto +100€/mes → scenario_expenses > base_expenses."""
    token = await _register_and_token(client, "scenario_add_expense@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={
                "months_ahead": 3,
                "recurring_expense_modifications": [
                    {"description": "Gym", "monthly_amount": "100.00", "action": "add"}
                ],
            },
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for month in data["monthly_results"]:
        assert float(month["scenario_expenses"]) > float(month["base_expenses"])


@pytest.mark.asyncio
async def test_remove_recurring_expense(client):
    """Eliminar gasto → scenario_expenses < base_expenses."""
    token = await _register_and_token(client, "scenario_remove_expense@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={
                "months_ahead": 3,
                "recurring_expense_modifications": [
                    {"description": "Netflix", "monthly_amount": "15.00", "action": "remove"}
                ],
            },
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for month in data["monthly_results"]:
        assert float(month["scenario_expenses"]) < float(month["base_expenses"])


@pytest.mark.asyncio
async def test_tax_impact_gross_provided(client):
    """Con gross_annual → campos tax_monthly_* presentes."""
    token = await _register_and_token(client, "scenario_tax_yes@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 3, "gross_annual": "35000.00", "tax_year": 2026},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for month in data["monthly_results"]:
        assert month["tax_monthly_base"] is not None
        assert month["tax_monthly_scenario"] is not None
        assert month["tax_monthly_delta"] is not None
    assert data["summary"]["total_tax_impact"] is not None


@pytest.mark.asyncio
async def test_tax_impact_not_provided(client):
    """Sin gross_annual → campos tax_monthly_* son None."""
    token = await _register_and_token(client, "scenario_tax_no@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 3},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for month in data["monthly_results"]:
        assert month["tax_monthly_base"] is None
        assert month["tax_monthly_scenario"] is None
        assert month["tax_monthly_delta"] is None
    assert data["summary"]["total_tax_impact"] is None


@pytest.mark.asyncio
async def test_euribor_no_mortgage(client):
    """Euríbor variación sin simulación hipotecaria guardada → mortgage_delta = 0."""
    token = await _register_and_token(client, "scenario_euribor_nomortgage@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 3, "euribor_variation_pct": "1.5"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    # Sin hipoteca guardada, el impacto debe ser 0 (o null si no aplica)
    assert data["mortgage_impact_per_month"] is not None
    assert float(data["mortgage_impact_per_month"]) == 0.0


@pytest.mark.asyncio
async def test_months_ahead_validation_too_large(client):
    """months_ahead=25 → 422."""
    token = await _register_and_token(client, "scenario_val1@test.com")
    resp = await client.post(
        "/api/v1/scenarios/analyze",
        json={"months_ahead": 25},
        headers=_auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_months_ahead_validation_zero(client):
    """months_ahead=0 → 422."""
    token = await _register_and_token(client, "scenario_val2@test.com")
    resp = await client.post(
        "/api/v1/scenarios/analyze",
        json={"months_ahead": 0},
        headers=_auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_monte_carlo_intervals_ordered(client):
    """P10 ≤ P50 ≤ P90 para cada mes."""
    token = await _register_and_token(client, "scenario_ordered@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 6, "salary_variation_pct": "10"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for month in data["monthly_results"]:
        p10 = float(month["scenario_net_p10"])
        p50 = float(month["scenario_net_p50"])
        p90 = float(month["scenario_net_p90"])
        assert p10 <= p50 <= p90, f"Orden P10≤P50≤P90 violado: {p10}, {p50}, {p90}"


@pytest.mark.asyncio
async def test_summary_fields_present(client):
    """Todos los campos del summary están presentes."""
    token = await _register_and_token(client, "scenario_summary@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 6},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    summary = resp.json()["summary"]
    required = [
        "period_months",
        "total_base_net",
        "total_scenario_net_p50",
        "total_net_improvement",
        "total_net_improvement_p10",
        "total_net_improvement_p90",
        "avg_monthly_improvement",
    ]
    for field in required:
        assert field in summary, f"Campo '{field}' ausente en summary"


@pytest.mark.asyncio
async def test_ml_unavailable_graceful(client):
    """Si ml-service no responde, devuelve 200 con ml_available=False."""
    token = await _register_and_token(client, "scenario_ml_unavail@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 3},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ml_available"] is False
    assert len(data["monthly_results"]) == 3


@pytest.mark.asyncio
async def test_analyze_response_schema(client):
    """La respuesta tiene todos los campos requeridos del schema."""
    token = await _register_and_token(client, "scenario_schema@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.post(
            "/api/v1/scenarios/analyze",
            json={"months_ahead": 3, "name": "Test Schema"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for field in ["name", "parameters", "historical_months_used", "ml_available", "monthly_results", "summary"]:
        assert field in data, f"Campo '{field}' ausente en ScenarioResponse"


# ---------------------------------------------------------------------------
# Tests unitarios de funciones puras
# ---------------------------------------------------------------------------


def test_monte_carlo_pure_function():
    """simulate_net_distribution devuelve P10 ≤ P50 ≤ P90."""
    import numpy as np
    from app.utils.monte_carlo import simulate_net_distribution

    rng = np.random.default_rng(42)
    p10, p50, p90 = simulate_net_distribution(
        income_p50=2500.0,
        income_p10=2000.0,
        income_p90=3000.0,
        expenses_p50=1800.0,
        expenses_p10=1500.0,
        expenses_p90=2100.0,
        n=1000,
        rng=rng,
    )
    assert p10 <= p50 <= p90
    # El neto esperado ≈ 2500 - 1800 = 700
    assert 400 < p50 < 1000


def test_apply_modifications_pure():
    """apply_scenario_modifications aplica los cambios correctamente."""
    from app.utils.monte_carlo import apply_scenario_modifications

    # +10% sueldo + 100€ gastos
    new_income, new_expenses = apply_scenario_modifications(
        income_p50=2500.0,
        expenses_p50=1800.0,
        salary_variation_pct=10.0,
        expense_delta_monthly=100.0,
    )
    assert abs(new_income - 2750.0) < 0.01
    assert abs(new_expenses - 1900.0) < 0.01


def test_apply_modifications_negative_salary():
    """Reducción de sueldo del 100% lleva el ingreso a 0."""
    from app.utils.monte_carlo import apply_scenario_modifications

    new_income, _ = apply_scenario_modifications(
        income_p50=2500.0,
        expenses_p50=1800.0,
        salary_variation_pct=-100.0,
        expense_delta_monthly=0.0,
    )
    assert new_income == 0.0


def test_monte_carlo_zero_sigma():
    """Con P10 == P50 == P90 (sin incertidumbre), los percentiles son iguales."""
    import numpy as np
    from app.utils.monte_carlo import simulate_net_distribution

    rng = np.random.default_rng(0)
    p10, p50, p90 = simulate_net_distribution(
        income_p50=2500.0,
        income_p10=2500.0,
        income_p90=2500.0,
        expenses_p50=1800.0,
        expenses_p10=1800.0,
        expenses_p90=1800.0,
        n=500,
        rng=rng,
    )
    # Con sigma=0 todos los percentiles deben ser iguales
    assert abs(p10 - p50) < 0.01
    assert abs(p50 - p90) < 0.01
    assert abs(p50 - 700.0) < 0.01
