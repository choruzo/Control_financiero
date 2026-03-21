import structlog
from fastapi import APIRouter

from app.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check del servicio ML."""
    logger.debug("health_check")
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "model_loaded": False,
    }
