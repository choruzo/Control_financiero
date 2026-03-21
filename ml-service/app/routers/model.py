import structlog
from fastapi import APIRouter

from app.schemas.model import ModelStatusResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status() -> ModelStatusResponse:
    """
    Devuelve el estado actual del modelo de categorización.

    En la Fase 3.1 no hay modelo cargado (stub).
    La Fase 3.2 implementará la carga real de DistilBERT.
    """
    logger.debug("model_status_request")
    return ModelStatusResponse(
        loaded=False,
        version=None,
        accuracy=None,
        last_trained=None,
        feedback_count=0,
    )
