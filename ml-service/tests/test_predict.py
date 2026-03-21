"""Tests del endpoint /predict y /feedback del ml-service.

En entorno de tests el modelo no está entrenado, por lo que el servicio
opera en modo degradado: confidence=0.0, model_version="degraded".
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_predict_degraded_mode(client: AsyncClient):
    """Sin modelo entrenado, el endpoint responde en modo degradado."""
    response = await client.post("/predict", json={"description": "Compra MERCADONA 12/03"})
    assert response.status_code == 200
    data = response.json()
    # En modo degradado: confianza 0, sin auto-asignación ni sugerencia
    assert data["confidence"] == 0.0
    assert data["auto_assigned"] is False
    assert data["suggested"] is False
    assert data["model_version"] == "degraded"
    # category_name es None cuando confidence == 0.0
    assert data["category_name"] is None


@pytest.mark.asyncio
async def test_predict_with_transaction_id(client: AsyncClient):
    response = await client.post(
        "/predict",
        json={"description": "TRANSFERENCIA RECIBIDA", "transaction_id": 42},
    )
    assert response.status_code == 200
    data = response.json()
    assert "confidence" in data
    assert "auto_assigned" in data
    assert "suggested" in data


@pytest.mark.asyncio
async def test_predict_empty_description_fails(client: AsyncClient):
    response = await client.post("/predict", json={"description": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_missing_description_fails(client: AsyncClient):
    response = await client.post("/predict", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_response_schema(client: AsyncClient):
    """Verifica que el schema de respuesta tenga todos los campos requeridos."""
    response = await client.post("/predict", json={"description": "REPSOL GASOLINERA"})
    assert response.status_code == 200
    data = response.json()
    required_fields = {"category_id", "category_name", "confidence", "auto_assigned", "suggested", "model_version"}
    assert required_fields.issubset(data.keys())


@pytest.mark.asyncio
async def test_feedback_accepted(client: AsyncClient):
    """El feedback siempre devuelve un feedback_id, aunque Redis no esté disponible."""
    response = await client.post(
        "/feedback",
        json={
            "transaction_id": 1,
            "description": "Compra MERCADONA",
            "predicted_category_id": None,
            "correct_category_id": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    # En tests Redis no está disponible → status="queued"
    assert data["status"] in ("stored", "queued")
    assert data["feedback_id"] is not None


@pytest.mark.asyncio
async def test_feedback_without_prediction(client: AsyncClient):
    response = await client.post(
        "/feedback",
        json={
            "transaction_id": 2,
            "description": "NÓMINA EMPRESA",
            "predicted_category_id": None,
            "correct_category_id": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("stored", "queued")


@pytest.mark.asyncio
async def test_feedback_returns_unique_ids(client: AsyncClient):
    """Cada petición de feedback genera un ID único."""
    payload = {
        "transaction_id": 3,
        "description": "LIDL SUPERMERCADO",
        "predicted_category_id": 9,
        "correct_category_id": 0,
    }
    r1 = await client.post("/feedback", json=payload)
    r2 = await client.post("/feedback", json=payload)
    assert r1.json()["feedback_id"] != r2.json()["feedback_id"]
