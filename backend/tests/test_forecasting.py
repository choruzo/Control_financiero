"""
Tests de integración para la predicción de flujo de caja (Fase 4.1).

Cubre:
- GET /api/v1/analytics/forecast: endpoint protegido con auth
- Degradación graceful cuando ml-service no está disponible
- Respuesta correcta con ml-service mockeado
- Validación de parámetros (months fuera de rango)
- Tarea Celery trigger_forecast_retrain
"""

from __future__ import annotations

import pytest
import respx
import httpx
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_token(client: AsyncClient, email: str = "forecast@test.com") -> str:
    """Registra un usuario y devuelve el access_token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


ML_FORECAST_RESPONSE = {
    "predictions": [
        {
            "year": 2026,
            "month": 4,
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
    ],
    "model_used": "prophet",
    "model_version": "1.0",
    "data_months_provided": 3,
}


# ---------------------------------------------------------------------------
# Tests de autenticación
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_requires_auth(client):
    """El endpoint de forecast requiere autenticación."""
    resp = await client.get("/api/v1/analytics/forecast")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests con usuario autenticado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_returns_valid_response_no_data(client):
    """Sin transacciones históricas, devuelve respuesta válida (degradada o vacía)."""
    token = await _register_and_token(client, "forecast_nodata@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.get(
            "/api/v1/analytics/forecast?months=3",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert "model_used" in data
    assert "ml_available" in data
    assert "historical_months_used" in data


@pytest.mark.asyncio
async def test_forecast_months_validation_too_large(client):
    """months=13 debe retornar 422."""
    token = await _register_and_token(client, "forecast_val1@test.com")
    resp = await client.get(
        "/api/v1/analytics/forecast?months=13",
        headers=_auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_forecast_months_validation_zero(client):
    """months=0 debe retornar 422."""
    token = await _register_and_token(client, "forecast_val2@test.com")
    resp = await client.get(
        "/api/v1/analytics/forecast?months=0",
        headers=_auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_forecast_default_months(client):
    """Sin parámetro months, usa el valor por defecto (6)."""
    token = await _register_and_token(client, "forecast_default@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.get(
            "/api/v1/analytics/forecast",
            headers=_auth(token),
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_forecast_ml_unavailable_graceful(client):
    """Si ml-service no responde, devuelve ml_available=False sin error 500."""
    token = await _register_and_token(client, "forecast_unavail@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        resp = await client.get(
            "/api/v1/analytics/forecast?months=3",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ml_available"] is False


@pytest.mark.asyncio
async def test_forecast_ml_timeout_graceful(client):
    """Si ml-service da timeout, devuelve ml_available=False sin error 500."""
    token = await _register_and_token(client, "forecast_timeout@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            side_effect=httpx.TimeoutException("Timeout")
        )
        resp = await client.get(
            "/api/v1/analytics/forecast?months=3",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ml_available"] is False


@pytest.mark.asyncio
async def test_forecast_response_schema(client):
    """La respuesta tiene todos los campos requeridos."""
    token = await _register_and_token(client, "forecast_schema@test.com")

    with respx.mock:
        respx.post("http://ml-service:8001/forecast").mock(
            return_value=httpx.Response(200, json=ML_FORECAST_RESPONSE)
        )
        resp = await client.get(
            "/api/v1/analytics/forecast?months=1",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    for field in [
        "predictions",
        "model_used",
        "model_version",
        "historical_months_used",
        "ml_available",
    ]:
        assert field in data, f"Campo '{field}' ausente en CashflowForecastResponse"


# ---------------------------------------------------------------------------
# Tests de la Celery task
# ---------------------------------------------------------------------------


def test_trigger_forecast_retrain_task_ml_unavailable():
    """La task Celery maneja correctamente un ml-service no disponible."""
    from unittest.mock import patch

    from app.tasks.forecasting import trigger_forecast_retrain

    mock_result = {"status": "error", "ml_available": False, "reason": "Connection refused"}
    with patch(
        "app.tasks.forecasting.ml_client.trigger_forecast_retrain_sync",
        return_value=mock_result,
    ):
        result = trigger_forecast_retrain()

    assert result["status"] == "error"
    assert result["ml_available"] is False


def test_trigger_forecast_retrain_task_started():
    """La task Celery registra correctamente cuando el reentrenamiento se inicia."""
    from unittest.mock import patch

    from app.tasks.forecasting import trigger_forecast_retrain

    mock_result = {
        "status": "started",
        "data_series_count": 15,
        "ml_available": True,
    }
    with patch(
        "app.tasks.forecasting.ml_client.trigger_forecast_retrain_sync",
        return_value=mock_result,
    ):
        result = trigger_forecast_retrain()

    assert result["status"] == "started"
    assert result["ml_available"] is True


def test_trigger_forecast_retrain_task_skipped():
    """La task Celery maneja correctamente el caso de datos insuficientes."""
    from unittest.mock import patch

    from app.tasks.forecasting import trigger_forecast_retrain

    mock_result = {
        "status": "skipped",
        "data_series_count": 2,
        "reason": "Series insuficientes",
        "ml_available": True,
    }
    with patch(
        "app.tasks.forecasting.ml_client.trigger_forecast_retrain_sync",
        return_value=mock_result,
    ):
        result = trigger_forecast_retrain()

    assert result["status"] == "skipped"
