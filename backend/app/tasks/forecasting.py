"""
Celery task para el reentrenamiento mensual del modelo de forecasting.

Dispara POST /forecast/retrain en el ml-service, que lee las series
históricas acumuladas en Redis y reentrena el LSTM.

El Celery Beat ejecuta esta task el primer día de cada mes a las 4AM.
"""

import structlog

from app.services.ml_client import ml_client
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.forecasting.trigger_forecast_retrain")
def trigger_forecast_retrain() -> dict:
    """
    Dispara el reentrenamiento del modelo LSTM de forecasting.

    El ml-service usa las series históricas almacenadas en Redis
    (acumuladas de las peticiones de forecast de usuarios reales)
    para actualizar el modelo.

    Returns:
        dict con status, data_series_count y ml_available.
    """
    logger.info("forecast_retrain_task_started")

    result = ml_client.trigger_forecast_retrain_sync()
    status = result.get("status", "unknown")
    ml_available = result.get("ml_available", False)

    if not ml_available:
        logger.warning("forecast_retrain_service_unavailable", reason=result.get("reason"))
    elif status == "started":
        logger.info(
            "forecast_retrain_triggered",
            data_series=result.get("data_series_count", 0),
        )
    elif status == "skipped":
        logger.info("forecast_retrain_skipped", reason=result.get("reason"))
    elif status == "in_progress":
        logger.info("forecast_retrain_already_running")
    else:
        logger.warning("forecast_retrain_unexpected_status", status=status)

    return result
