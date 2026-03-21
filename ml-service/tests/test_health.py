import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data


@pytest.mark.asyncio
async def test_health_model_not_loaded(client: AsyncClient):
    response = await client.get("/health")
    data = response.json()
    assert data["model_loaded"] is False


@pytest.mark.asyncio
async def test_model_status_not_loaded(client: AsyncClient):
    response = await client.get("/model/status")
    assert response.status_code == 200
    data = response.json()
    assert data["loaded"] is False
    assert data["version"] is None
    assert data["accuracy"] is None
    assert data["last_trained"] is None
    assert data["feedback_count"] == 0
