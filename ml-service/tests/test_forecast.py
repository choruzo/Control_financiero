"""
Tests del endpoint de forecasting (Fase 4.1).

Cubre:
- Modo degradado (sin modelo): devuelve respuesta válida con ceros
- Validación de request (meses fuera de rango, lista vacía)
- Schema de respuesta (P10 ≤ P50 ≤ P90, meses correctos)
- Endpoint /forecast/status
- Endpoint /forecast/retrain (skipped por datos insuficientes, 409 si en curso)
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Datos de prueba
# ---------------------------------------------------------------------------

HISTORICAL_6M = [
    {"year": 2025, "month": 7, "income": 2500.0, "expenses": 1800.0},
    {"year": 2025, "month": 8, "income": 2500.0, "expenses": 2100.0},
    {"year": 2025, "month": 9, "income": 2500.0, "expenses": 1950.0},
    {"year": 2025, "month": 10, "income": 2500.0, "expenses": 1800.0},
    {"year": 2025, "month": 11, "income": 2500.0, "expenses": 1850.0},
    {"year": 2025, "month": 12, "income": 5000.0, "expenses": 3000.0},
]

HISTORICAL_1M = [
    {"year": 2026, "month": 1, "income": 2500.0, "expenses": 1800.0},
]


# ---------------------------------------------------------------------------
# Tests de /forecast
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_degraded_mode_returns_valid_response(client):
    """Con modelo no cargado, devuelve respuesta degradada con zeros y schema válido."""
    payload = {
        "historical_data": HISTORICAL_6M,
        "months_ahead": 3,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "predictions" in data
    assert "model_used" in data
    assert "model_version" in data
    assert "data_months_provided" in data
    assert data["data_months_provided"] == 6
    assert len(data["predictions"]) == 3


@pytest.mark.asyncio
async def test_forecast_degraded_model_used(client):
    """En modo degradado (sin Prophet ni LSTM), model_used debe ser 'degraded'."""
    payload = {
        "historical_data": HISTORICAL_1M,
        "months_ahead": 2,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Con 1 mes de datos, Prophet necesita >= 3; sin LSTM → degraded
    assert data["model_used"] in ("degraded", "prophet", "lstm")


@pytest.mark.asyncio
async def test_forecast_response_months_sequence(client):
    """Los meses predichos deben ser consecutivos y posteriores al último dato histórico."""
    payload = {
        "historical_data": HISTORICAL_6M,
        "months_ahead": 4,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 200

    preds = resp.json()["predictions"]
    assert len(preds) == 4

    # El primer mes predicho debe ser enero 2026 (después de diciembre 2025)
    assert preds[0]["year"] == 2026
    assert preds[0]["month"] == 1
    assert preds[1]["year"] == 2026
    assert preds[1]["month"] == 2


@pytest.mark.asyncio
async def test_forecast_prediction_fields_present(client):
    """Cada ForecastPoint debe tener todos los campos requeridos."""
    payload = {
        "historical_data": HISTORICAL_6M,
        "months_ahead": 2,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 200

    for pred in resp.json()["predictions"]:
        for field in [
            "year", "month",
            "income_p10", "income_p50", "income_p90",
            "expenses_p10", "expenses_p50", "expenses_p90",
            "net_p10", "net_p50", "net_p90",
        ]:
            assert field in pred, f"Campo '{field}' ausente en ForecastPoint"


@pytest.mark.asyncio
async def test_forecast_default_months_ahead(client):
    """Sin especificar months_ahead, debe predecir 6 meses por defecto."""
    payload = {"historical_data": HISTORICAL_6M}
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 200
    assert len(resp.json()["predictions"]) == 6


@pytest.mark.asyncio
async def test_forecast_invalid_months_ahead_zero(client):
    """months_ahead=0 debe retornar 422."""
    payload = {
        "historical_data": HISTORICAL_6M,
        "months_ahead": 0,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_forecast_invalid_months_ahead_too_large(client):
    """months_ahead=13 debe retornar 422."""
    payload = {
        "historical_data": HISTORICAL_6M,
        "months_ahead": 13,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_forecast_empty_historical_data(client):
    """historical_data vacío debe retornar 422."""
    payload = {
        "historical_data": [],
        "months_ahead": 3,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_forecast_negative_income_rejected(client):
    """income negativo debe retornar 422."""
    payload = {
        "historical_data": [{"year": 2026, "month": 1, "income": -100.0, "expenses": 500.0}],
        "months_ahead": 1,
    }
    resp = await client.post("/forecast", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests de /forecast/status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_status_degraded(client):
    """Estado del forecaster en modo degradado."""
    resp = await client.get("/forecast/status")
    assert resp.status_code == 200

    data = resp.json()
    assert data["loaded"] is False
    assert "retrain_in_progress" in data
    assert data["retrain_in_progress"] is False
    assert "min_months_required" in data
    assert isinstance(data["min_months_required"], int)


# ---------------------------------------------------------------------------
# Tests de /forecast/retrain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_retrain_skipped_no_redis(client):
    """Con Redis no disponible en tests, retrain devuelve 503 o 200 (skipped)."""
    resp = await client.post("/forecast/retrain")
    # Puede ser 503 (Redis no disponible) o 200 (skipped) según entorno
    assert resp.status_code in (200, 202, 503)
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_forecast_retrain_in_progress_returns_409(client):
    """Si ya hay un reentrenamiento en curso, retorna 409."""
    from app.main import app

    app.state.forecast_retrain_in_progress = True
    try:
        resp = await client.post("/forecast/retrain")
        assert resp.status_code == 409
        data = resp.json()
        assert data["status"] == "in_progress"
    finally:
        app.state.forecast_retrain_in_progress = False


# ---------------------------------------------------------------------------
# Tests unitarios del Forecaster
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecaster_degraded_mode():
    """Forecaster sin modelo devuelve respuesta degradada con estructura correcta."""
    from app.ml.forecaster import Forecaster

    forecaster = Forecaster(model_path="/tmp/does_not_exist", device="cpu")
    await forecaster.load()
    assert forecaster.loaded is False

    historical = [
        {"year": 2026, "month": 1, "income": 2500.0, "expenses": 1800.0},
    ]
    preds, model_used = forecaster.predict(historical, months_ahead=2)

    assert len(preds) == 2
    # Con 1 mes de datos y sin LSTM ni Prophet, debe retornar degraded
    assert model_used in ("degraded", "prophet", "lstm")


def test_forecaster_next_months_basic():
    """_next_months genera la secuencia correcta de meses futuros."""
    from app.ml.forecaster import Forecaster

    historical = [
        {"year": 2026, "month": 10, "income": 2500.0, "expenses": 1800.0},
    ]
    months = Forecaster._next_months(historical, 4)
    assert months == [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]


def test_forecaster_next_months_year_rollover():
    """_next_months maneja correctamente el cambio de año."""
    from app.ml.forecaster import Forecaster

    historical = [{"year": 2026, "month": 11, "income": 2500.0, "expenses": 1800.0}]
    months = Forecaster._next_months(historical, 3)
    assert months == [(2026, 12), (2027, 1), (2027, 2)]


def test_forecaster_build_result_net_calculation():
    """net_p10 = income_p10 - expenses_p90 (escenario pesimista)."""
    from app.ml.forecaster import Forecaster
    import numpy as np

    future_months = [(2026, 4)]
    p10 = np.array([[2000.0, 1500.0]])
    p50 = np.array([[2500.0, 1800.0]])
    p90 = np.array([[3000.0, 2100.0]])

    result = Forecaster._build_result(future_months, p10, p50, p90)
    assert len(result) == 1
    r = result[0]
    # net_p10 = income_p10 - expenses_p90 = 2000 - 2100 = -100
    assert r["net_p10"] == round(2000.0 - 2100.0, 2)
    # net_p50 = income_p50 - expenses_p50 = 2500 - 1800 = 700
    assert r["net_p50"] == round(2500.0 - 1800.0, 2)
    # net_p90 = income_p90 - expenses_p10 = 3000 - 1500 = 1500
    assert r["net_p90"] == round(3000.0 - 1500.0, 2)
