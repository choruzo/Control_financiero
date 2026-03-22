"""
Celery task para el reentrenamiento incremental del modelo ML.

La task llama al endpoint POST /retrain del ml-service via HTTP síncrono.
Si el servicio no está disponible, la task termina sin error (degradación graceful).

El Celery Beat dispara esta task semanalmente (domingo 3AM, configurable en config.py).
"""

import structlog

from app.services.ml_client import ml_client
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.ml_retraining.trigger_ml_retrain")
def trigger_ml_retrain() -> dict:
    """
    Dispara el reentrenamiento incremental del modelo de categorización.

    Llama a POST /retrain en el ml-service y registra el resultado.
    Si el servicio no está disponible, registra un warning y termina con éxito
    (para no marcar la tarea como FAILURE en el broker).

    Returns:
        dict con el resultado del disparo: status, feedback_count, ml_available.
    """
    logger.info("ml_retrain_task_started")

    result = ml_client.trigger_retrain_sync()
    status = result.get("status", "unknown")
    ml_available = result.get("ml_available", False)

    if not ml_available:
        logger.warning("ml_retrain_service_unavailable", reason=result.get("reason"))
    elif status == "started":
        logger.info("ml_retrain_triggered", feedback_count=result.get("feedback_count", 0))
    elif status == "skipped":
        logger.info("ml_retrain_skipped", reason=result.get("reason"))
    elif status == "in_progress":
        logger.info("ml_retrain_already_running")
    else:
        logger.warning("ml_retrain_unexpected_status", status=status)

    return result
