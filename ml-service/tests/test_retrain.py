"""
Tests de integración para el endpoint POST /retrain y callbacks de reentrenamiento.

Redis y run_incremental_retrain se mockean para no requerir servicios externos.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import app
from app.routers.retrain import _backup_active_metadata, _on_retrain_complete


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_feedback_items(n: int) -> list[str]:
    """Genera N entradas de feedback como strings JSON (formato Redis)."""
    return [
        json.dumps({
            "id": f"uuid-{i}",
            "transaction_id": i,
            "description": f"Compra mercado {i}",
            "predicted_category_id": 0,
            "correct_category_id": 0,
            "timestamp": "2026-03-22T10:00:00+00:00",
        })
        for i in range(n)
    ]


def _mock_redis(lrange_return: list[str]):
    """Crea un mock de aioredis con lrange y llen configurados."""
    mock_r = AsyncMock()
    mock_r.lrange.return_value = lrange_return
    mock_r.llen.return_value = len(lrange_return)
    mock_r.rename = AsyncMock()
    mock_r.aclose = AsyncMock()
    return mock_r


@pytest.fixture(autouse=True)
def reset_retrain_state():
    """Restaura retrain_in_progress=False antes y después de cada test."""
    app.state.retrain_in_progress = False
    yield
    app.state.retrain_in_progress = False


# ── POST /retrain ─────────────────────────────────────────────────────────────


async def test_retrain_blocked_when_in_progress(client):
    """Devuelve 409 si ya hay un reentrenamiento en curso."""
    app.state.retrain_in_progress = True

    response = await client.post("/retrain")

    assert response.status_code == 409
    data = response.json()
    assert data["status"] == "in_progress"


async def test_retrain_skipped_insufficient_feedback(client):
    """Devuelve 200 con status=skipped si hay menos feedback del mínimo."""
    mock_r = _mock_redis(_make_feedback_items(2))  # 2 < 10 (mínimo por defecto)

    with patch("app.routers.retrain.aioredis.from_url", return_value=mock_r):
        response = await client.post("/retrain")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert data["feedback_count"] == 2
    assert "insuficiente" in data["reason"].lower()


async def test_retrain_started_with_sufficient_feedback(client):
    """Devuelve 202 con status=started cuando hay feedback suficiente."""
    mock_r = _mock_redis(_make_feedback_items(15))  # 15 >= 10

    with (
        patch("app.routers.retrain.aioredis.from_url", return_value=mock_r),
        patch("app.routers.retrain.run_incremental_retrain") as mock_train,
        patch("app.routers.retrain.asyncio.get_running_loop") as mock_loop,
    ):
        # El executor no ejecuta nada en el test
        mock_loop_instance = MagicMock()
        mock_loop_instance.run_in_executor = MagicMock()
        mock_loop.return_value = mock_loop_instance

        response = await client.post("/retrain")

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "started"
    assert data["feedback_count"] == 15


async def test_retrain_sets_in_progress_flag(client):
    """El flag retrain_in_progress se pone a True al iniciar el reentrenamiento."""
    mock_r = _mock_redis(_make_feedback_items(15))

    with (
        patch("app.routers.retrain.aioredis.from_url", return_value=mock_r),
        patch("app.routers.retrain.asyncio.get_running_loop") as mock_loop,
    ):
        mock_loop_instance = MagicMock()
        mock_loop_instance.run_in_executor = MagicMock()
        mock_loop.return_value = mock_loop_instance

        await client.post("/retrain")

    assert app.state.retrain_in_progress is True


async def test_retrain_redis_error_returns_503(client):
    """Devuelve 503 si Redis no está disponible."""
    with patch("app.routers.retrain.aioredis.from_url", side_effect=Exception("Redis down")):
        response = await client.post("/retrain")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"


# ── _on_retrain_complete ──────────────────────────────────────────────────────


async def test_on_retrain_complete_failure_resets_flag():
    """Si el entrenamiento falla, el flag se resetea a False."""
    app.state.retrain_in_progress = True

    await _on_retrain_complete(app, metadata={}, success=False)

    assert app.state.retrain_in_progress is False


async def test_on_retrain_complete_promotes_better_model(tmp_path):
    """Promueve el candidato si su accuracy es mayor que el modelo activo."""
    # Preparar candidato
    candidate_path = tmp_path / "categorizer_candidate"
    candidate_path.mkdir()
    active_path = tmp_path / "categorizer"
    active_path.mkdir()

    active_meta = {"version": "1.0", "accuracy": 0.80}
    (active_path / "metadata.json").write_text(json.dumps(active_meta), encoding="utf-8")
    (candidate_path / "metadata.json").write_text(
        json.dumps({"version": "1.1", "accuracy": 0.88}), encoding="utf-8"
    )

    app.state.model_manager.metadata = active_meta
    app.state.retrain_in_progress = True

    # Mock de reload y Redis
    app.state.model_manager.reload = AsyncMock()
    mock_r = _mock_redis([])

    with (
        patch("app.routers.retrain.Path") as mock_path_cls,
        patch("app.routers.retrain.aioredis.from_url", return_value=mock_r),
        patch("app.routers.retrain.shutil.rmtree"),
        patch("app.routers.retrain.shutil.move"),
        patch("app.routers.retrain._backup_active_metadata"),
    ):
        # Simular rutas apuntando a tmp_path
        def _side_effect(path_str):
            if "categorizer_candidate" in str(path_str):
                return candidate_path
            if "categorizer" in str(path_str):
                return active_path
            return MagicMock()

        mock_path_cls.return_value.__truediv__ = lambda self, x: (
            candidate_path if "candidate" in str(x) else active_path
        )

        metadata = {"version": "1.1", "accuracy": 0.88}
        await _on_retrain_complete(app, metadata=metadata, success=True)

    # El modelo debe haberse recargado
    app.state.model_manager.reload.assert_called_once()
    assert app.state.retrain_in_progress is False


async def test_on_retrain_complete_rejects_worse_model():
    """Descarta el candidato si su accuracy cae más del 2% respecto al activo."""
    app.state.model_manager.metadata = {"version": "1.0", "accuracy": 0.85}
    app.state.retrain_in_progress = True
    app.state.model_manager.reload = AsyncMock()

    with (
        patch("app.routers.retrain.Path") as mock_path_cls,
        patch("app.routers.retrain.shutil.rmtree") as mock_rmtree,
    ):
        mock_candidate = MagicMock()
        mock_candidate.exists.return_value = True
        mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_candidate)

        # accuracy 0.75 < 0.85 - 0.02 = 0.83 → debe descartarse
        await _on_retrain_complete(app, metadata={"accuracy": 0.75}, success=True)

    app.state.model_manager.reload.assert_not_called()
    assert app.state.retrain_in_progress is False


async def test_on_retrain_complete_promotes_within_tolerance():
    """Promueve si la accuracy es solo 1% menor (dentro de la tolerancia del 2%)."""
    app.state.model_manager.metadata = {"version": "1.0", "accuracy": 0.85}
    app.state.retrain_in_progress = True
    app.state.model_manager.reload = AsyncMock()

    mock_r = _mock_redis([])

    with (
        patch("app.routers.retrain.Path") as mock_path_cls,
        patch("app.routers.retrain.aioredis.from_url", return_value=mock_r),
        patch("app.routers.retrain.shutil.rmtree"),
        patch("app.routers.retrain.shutil.move"),
        patch("app.routers.retrain._backup_active_metadata"),
    ):
        mock_candidate = MagicMock()
        mock_candidate.exists.return_value = True
        mock_active = MagicMock()
        mock_active.exists.return_value = True

        def _div(self, x):
            return mock_candidate if "candidate" in str(x) else mock_active

        mock_path_cls.return_value.__truediv__ = _div

        # accuracy 0.84 >= 0.85 - 0.02 = 0.83 → debe promoverse
        await _on_retrain_complete(app, metadata={"accuracy": 0.84}, success=True)

    app.state.model_manager.reload.assert_called_once()


# ── GET /model/status con retrain_in_progress ─────────────────────────────────


async def test_model_status_shows_retrain_in_progress(client):
    """GET /model/status refleja el flag retrain_in_progress."""
    app.state.retrain_in_progress = True
    mock_r = AsyncMock()
    mock_r.llen.return_value = 5
    mock_r.aclose = AsyncMock()

    with patch("app.routers.model.aioredis.from_url", return_value=mock_r):
        response = await client.get("/model/status")

    assert response.status_code == 200
    data = response.json()
    assert data["retrain_in_progress"] is True


async def test_model_status_includes_real_feedback_count(client):
    """GET /model/status devuelve el feedback_count real de Redis."""
    mock_r = AsyncMock()
    mock_r.llen.return_value = 8
    mock_r.aclose = AsyncMock()

    with patch("app.routers.model.aioredis.from_url", return_value=mock_r):
        response = await client.get("/model/status")

    assert response.status_code == 200
    data = response.json()
    assert data["feedback_count"] == 8
