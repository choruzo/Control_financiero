import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_predict_returns_stub_response(client: AsyncClient):
    response = await client.post("/predict", json={"description": "Compra MERCADONA 12/03"})
    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] is None
    assert data["category_name"] is None
    assert data["confidence"] == 0.0
    assert data["auto_assigned"] is False
    assert data["suggested"] is False
    assert data["model_version"] == "stub"


@pytest.mark.asyncio
async def test_predict_with_transaction_id(client: AsyncClient):
    response = await client.post(
        "/predict",
        json={"description": "TRANSFERENCIA RECIBIDA", "transaction_id": 42},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_version"] == "stub"


@pytest.mark.asyncio
async def test_predict_empty_description_fails(client: AsyncClient):
    response = await client.post("/predict", json={"description": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_missing_description_fails(client: AsyncClient):
    response = await client.post("/predict", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_feedback_accepted(client: AsyncClient):
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
    assert data["status"] == "received"
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
    assert data["status"] == "received"
