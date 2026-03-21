import json
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Request

from app.config import settings
from app.schemas.feedback import FeedbackRequest, FeedbackResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

FEEDBACK_KEY = "ml:feedback"


@router.post("", response_model=FeedbackResponse)
async def receive_feedback(request: FeedbackRequest, req: Request) -> FeedbackResponse:
    """
    Recibe y persiste el feedback del usuario sobre una predicción.

    El feedback se almacena en Redis (lista ml:feedback) para su uso en
    el reentrenamiento incremental de la Fase 3.3.
    """
    feedback_id = str(uuid.uuid4())

    entry = {
        "id": feedback_id,
        "transaction_id": request.transaction_id,
        "description": request.description,
        "predicted_category_id": request.predicted_category_id,
        "correct_category_id": request.correct_category_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis.rpush(FEEDBACK_KEY, json.dumps(entry))
        await redis.aclose()
        status = "stored"
        message = "Feedback almacenado para el próximo reentrenamiento."
    except Exception as exc:
        logger.warning("feedback_redis_error", error=str(exc))
        status = "queued"
        message = "Redis no disponible. El feedback se procesará cuando el servicio esté activo."

    logger.info(
        "feedback_received",
        feedback_id=feedback_id,
        transaction_id=request.transaction_id,
        predicted=request.predicted_category_id,
        correct=request.correct_category_id,
        status=status,
    )

    return FeedbackResponse(
        status=status,
        message=message,
        feedback_id=feedback_id,
    )
