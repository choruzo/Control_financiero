"""
Tests para el cliente ML (services/ml_client.py) y el router /api/v1/ml.

Se mockea httpx con respx para no depender del ml-service real.
"""

import pytest
import httpx
import respx
from httpx import AsyncClient, Response

from app.services.ml_client import MLClient
from app.schemas.ml import MLFeedbackRequest

ML_BASE = "http://ml-service:8001"

# Excepción reutilizable para simular servicio caído
_CONNECT_ERROR = httpx.ConnectError("connection refused")


# ── Helper fixtures ───────────────────────────────────────────────────────────


def _predict_payload() -> dict:
    return {
        "category_id": 5,
        "category_name": "Alimentación",
        "confidence": 0.92,
        "auto_assigned": True,
        "suggested": False,
        "model_version": "v1.0",
    }


def _feedback_payload() -> dict:
    return {
        "status": "received",
        "message": "Feedback registrado.",
        "feedback_id": "abc12345",
    }


def _status_payload() -> dict:
    return {
        "loaded": True,
        "version": "v1.0",
        "accuracy": 0.87,
        "last_trained": "2026-03-01T00:00:00",
        "feedback_count": 12,
    }


# ── MLClient.predict ──────────────────────────────────────────────────────────


@respx.mock
async def test_predict_success():
    respx.post(f"{ML_BASE}/predict").mock(return_value=Response(200, json=_predict_payload()))
    client = MLClient(base_url=ML_BASE)
    result = await client.predict("Compra MERCADONA", transaction_id=10)

    assert result.ml_available is True
    assert result.category_id == 5
    assert result.category_name == "Alimentación"
    assert result.confidence == 0.92
    assert result.auto_assigned is True
    assert result.model_version == "v1.0"


@respx.mock
async def test_predict_service_unavailable_returns_degraded():
    respx.post(f"{ML_BASE}/predict").mock(side_effect=_CONNECT_ERROR)
    client = MLClient(base_url=ML_BASE)
    result = await client.predict("TRANSFERENCIA")

    assert result.ml_available is False
    assert result.category_id is None
    assert result.confidence == 0.0
    assert result.model_version == "unavailable"


@respx.mock
async def test_predict_http_error_returns_degraded():
    respx.post(f"{ML_BASE}/predict").mock(return_value=Response(503))
    client = MLClient(base_url=ML_BASE)
    result = await client.predict("Pago recibo")

    assert result.ml_available is False
    assert result.model_version == "unavailable"


@respx.mock
async def test_predict_stub_response():
    stub = {
        "category_id": None,
        "category_name": None,
        "confidence": 0.0,
        "auto_assigned": False,
        "suggested": False,
        "model_version": "stub",
    }
    respx.post(f"{ML_BASE}/predict").mock(return_value=Response(200, json=stub))
    client = MLClient(base_url=ML_BASE)
    result = await client.predict("NÓMINA EMPRESA")

    assert result.ml_available is True
    assert result.model_version == "stub"
    assert result.category_id is None


# ── MLClient.send_feedback ────────────────────────────────────────────────────


@respx.mock
async def test_feedback_success():
    respx.post(f"{ML_BASE}/feedback").mock(return_value=Response(200, json=_feedback_payload()))
    client = MLClient(base_url=ML_BASE)
    req = MLFeedbackRequest(
        transaction_id=1,
        description="Compra MERCADONA",
        predicted_category_id=None,
        correct_category_id=5,
    )
    result = await client.send_feedback(req)

    assert result.ml_available is True
    assert result.status == "received"
    assert result.feedback_id == "abc12345"


@respx.mock
async def test_feedback_service_unavailable_returns_queued():
    respx.post(f"{ML_BASE}/feedback").mock(side_effect=_CONNECT_ERROR)
    client = MLClient(base_url=ML_BASE)
    req = MLFeedbackRequest(
        transaction_id=2,
        description="Taxi",
        predicted_category_id=3,
        correct_category_id=4,
    )
    result = await client.send_feedback(req)

    assert result.ml_available is False
    assert result.status == "queued"


# ── MLClient.get_model_status ─────────────────────────────────────────────────


@respx.mock
async def test_model_status_success():
    respx.get(f"{ML_BASE}/model/status").mock(return_value=Response(200, json=_status_payload()))
    client = MLClient(base_url=ML_BASE)
    status = await client.get_model_status()

    assert status["ml_available"] is True
    assert status["loaded"] is True
    assert status["accuracy"] == 0.87


@respx.mock
async def test_model_status_service_unavailable():
    respx.get(f"{ML_BASE}/model/status").mock(side_effect=httpx.ConnectError("timeout"))
    client = MLClient(base_url=ML_BASE)
    status = await client.get_model_status()

    assert status["ml_available"] is False
    assert status["loaded"] is False


# ── MLClient.health_check ─────────────────────────────────────────────────────


@respx.mock
async def test_health_check_ok():
    respx.get(f"{ML_BASE}/health").mock(return_value=Response(200, json={"status": "ok"}))
    client = MLClient(base_url=ML_BASE)
    assert await client.health_check() is True


@respx.mock
async def test_health_check_service_down():
    respx.get(f"{ML_BASE}/health").mock(side_effect=_CONNECT_ERROR)
    client = MLClient(base_url=ML_BASE)
    assert await client.health_check() is False


# ── Router /api/v1/ml (integración) ──────────────────────────────────────────


async def _get_token(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "ml_test@example.com", "password": "testpassword"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "ml_test@example.com", "password": "testpassword"},
    )
    return resp.json()["access_token"]


@respx.mock
async def test_router_predict_endpoint(client: AsyncClient):
    respx.post(f"{ML_BASE}/predict").mock(return_value=Response(200, json=_predict_payload()))
    token = await _get_token(client)

    response = await client.post(
        "/api/v1/ml/predict",
        json={"description": "Compra MERCADONA"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == 5
    assert data["ml_available"] is True


@respx.mock
async def test_router_predict_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/ml/predict", json={"description": "test"})
    assert response.status_code == 401


@respx.mock
async def test_router_feedback_endpoint(client: AsyncClient):
    respx.post(f"{ML_BASE}/feedback").mock(return_value=Response(200, json=_feedback_payload()))
    token = await _get_token(client)

    response = await client.post(
        "/api/v1/ml/feedback",
        json={
            "transaction_id": 1,
            "description": "Compra MERCADONA",
            "predicted_category_id": None,
            "correct_category_id": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"


@respx.mock
async def test_router_status_endpoint(client: AsyncClient):
    respx.get(f"{ML_BASE}/model/status").mock(return_value=Response(200, json=_status_payload()))
    token = await _get_token(client)

    response = await client.get(
        "/api/v1/ml/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["loaded"] is True
    assert data["ml_available"] is True


@respx.mock
async def test_router_predict_ml_unavailable_still_returns_200(client: AsyncClient):
    """El endpoint devuelve 200 aunque el ml-service esté caído (respuesta degradada)."""
    respx.post(f"{ML_BASE}/predict").mock(side_effect=_CONNECT_ERROR)
    token = await _get_token(client)

    response = await client.post(
        "/api/v1/ml/predict",
        json={"description": "Pago luz"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ml_available"] is False
    assert data["model_version"] == "unavailable"
