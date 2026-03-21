import structlog
from fastapi import APIRouter, Request

from app.config import settings
from app.ml.model_manager import ModelManager

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(req: Request):
    """Health check del servicio ML con estado real del modelo."""
    manager: ModelManager = req.app.state.model_manager
    logger.debug("health_check", model_loaded=manager.loaded)
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "model_loaded": manager.loaded,
    }
