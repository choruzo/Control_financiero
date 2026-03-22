import structlog
import redis.asyncio as aioredis
from fastapi import APIRouter, Request

from app.config import settings
from app.ml.model_manager import ModelManager
from app.schemas.model import ModelStatusResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/model", tags=["model"])

FEEDBACK_KEY = "ml:feedback"


@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status(req: Request) -> ModelStatusResponse:
    """Devuelve el estado actual del modelo de categorización."""
    manager: ModelManager = req.app.state.model_manager
    status = manager.get_status()

    # Leer feedback_count real desde Redis
    feedback_count = 0
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        feedback_count = await redis.llen(FEEDBACK_KEY)
        await redis.aclose()
    except Exception as exc:
        logger.warning("model_status_redis_error", error=str(exc))

    retrain_in_progress = getattr(req.app.state, "retrain_in_progress", False)

    logger.debug("model_status_request", loaded=status["loaded"], feedback_count=feedback_count)
    return ModelStatusResponse(
        **status,
        feedback_count=feedback_count,
        retrain_in_progress=retrain_in_progress,
    )
