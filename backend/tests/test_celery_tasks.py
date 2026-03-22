"""
Tests para las Celery tasks de ML (backend/app/tasks/ml_retraining.py)
y el método síncrono trigger_retrain_sync del MLClient.

Se mockea httpx.Client para no depender del ml-service real.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.ml_client import MLClient
from app.tasks.ml_retraining import trigger_ml_retrain

ML_BASE = "http://ml-service:8001"


# ── MLClient.trigger_retrain_sync ─────────────────────────────────────────────


def test_trigger_retrain_sync_started():
    """Devuelve status=started cuando el ml-service responde 202."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "started", "feedback_count": 15}
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.post.return_value = mock_response

    with patch("app.services.ml_client.httpx.Client", return_value=mock_client_instance):
        client = MLClient(base_url=ML_BASE)
        result = client.trigger_retrain_sync()

    assert result["status"] == "started"
    assert result["ml_available"] is True
    assert result["feedback_count"] == 15


def test_trigger_retrain_sync_skipped():
    """Devuelve status=skipped cuando hay feedback insuficiente."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "skipped",
        "feedback_count": 3,
        "reason": "Feedback insuficiente",
    }
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.post.return_value = mock_response

    with patch("app.services.ml_client.httpx.Client", return_value=mock_client_instance):
        client = MLClient(base_url=ML_BASE)
        result = client.trigger_retrain_sync()

    assert result["status"] == "skipped"
    assert result["ml_available"] is True


def test_trigger_retrain_sync_service_unavailable():
    """Devuelve ml_available=False y status=error si el servicio está caído."""
    with patch(
        "app.services.ml_client.httpx.Client",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        client = MLClient(base_url=ML_BASE)
        result = client.trigger_retrain_sync()

    assert result["ml_available"] is False
    assert result["status"] == "error"
    assert "reason" in result


def test_trigger_retrain_sync_http_error():
    """Devuelve ml_available=False si el ml-service responde con error HTTP."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=MagicMock()
    )

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.post.return_value = mock_response

    with patch("app.services.ml_client.httpx.Client", return_value=mock_client_instance):
        client = MLClient(base_url=ML_BASE)
        result = client.trigger_retrain_sync()

    assert result["ml_available"] is False
    assert result["status"] == "error"


# ── trigger_ml_retrain task ───────────────────────────────────────────────────


def test_celery_task_calls_ml_client():
    """La task llama a trigger_retrain_sync y devuelve el resultado."""
    expected = {"status": "started", "feedback_count": 12, "ml_available": True}

    with patch("app.tasks.ml_retraining.ml_client") as mock_ml_client:
        mock_ml_client.trigger_retrain_sync.return_value = expected
        result = trigger_ml_retrain()

    mock_ml_client.trigger_retrain_sync.assert_called_once()
    assert result == expected


def test_celery_task_graceful_when_service_down():
    """La task no lanza excepción si el ml-service está caído."""
    unavailable = {"status": "error", "ml_available": False, "reason": "connection refused"}

    with patch("app.tasks.ml_retraining.ml_client") as mock_ml_client:
        mock_ml_client.trigger_retrain_sync.return_value = unavailable
        result = trigger_ml_retrain()  # No debe lanzar excepción

    assert result["ml_available"] is False


def test_celery_task_graceful_when_skipped():
    """La task termina correctamente cuando el reentrenamiento se omite."""
    skipped = {"status": "skipped", "feedback_count": 2, "ml_available": True}

    with patch("app.tasks.ml_retraining.ml_client") as mock_ml_client:
        mock_ml_client.trigger_retrain_sync.return_value = skipped
        result = trigger_ml_retrain()

    assert result["status"] == "skipped"


def test_celery_task_graceful_when_in_progress():
    """La task termina correctamente si ya hay un reentrenamiento en curso."""
    in_progress = {"status": "in_progress", "feedback_count": 0, "ml_available": True}

    with patch("app.tasks.ml_retraining.ml_client") as mock_ml_client:
        mock_ml_client.trigger_retrain_sync.return_value = in_progress
        result = trigger_ml_retrain()

    assert result["status"] == "in_progress"
