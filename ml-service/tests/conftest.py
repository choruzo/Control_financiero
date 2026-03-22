import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ml.forecaster import Forecaster
from app.ml.model_manager import ModelManager


@pytest.fixture(autouse=True, scope="session")
async def setup_model_manager():
    """Inicializa ModelManager y Forecaster en modo degradado para tests."""
    manager = ModelManager(model_path="/tmp/nonexistent_test_model", device="cpu")
    await manager.load()  # No hay modelo → modo degradado (loaded=False)
    app.state.model_manager = manager
    app.state.retrain_in_progress = False

    forecaster = Forecaster(model_path="/tmp/nonexistent_test_forecaster", device="cpu")
    await forecaster.load()  # No hay modelo → modo degradado (loaded=False)
    app.state.forecaster = forecaster
    app.state.forecast_retrain_in_progress = False


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
