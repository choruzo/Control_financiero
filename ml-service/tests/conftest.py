import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ml.model_manager import ModelManager


@pytest.fixture(autouse=True, scope="session")
async def setup_model_manager():
    """Inicializa el ModelManager en modo degradado para tests (sin modelo en disco)."""
    manager = ModelManager(model_path="/tmp/nonexistent_test_model", device="cpu")
    await manager.load()  # No hay modelo → queda en modo degradado (loaded=False)
    app.state.model_manager = manager
    app.state.retrain_in_progress = False


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
