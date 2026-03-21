import structlog
from fastapi import APIRouter, Request

from app.ml.model_manager import ModelManager
from app.schemas.model import ModelStatusResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status(req: Request) -> ModelStatusResponse:
    """Devuelve el estado actual del modelo de categorización."""
    manager: ModelManager = req.app.state.model_manager
    status = manager.get_status()
    logger.debug("model_status_request", loaded=status["loaded"])
    return ModelStatusResponse(**status)
