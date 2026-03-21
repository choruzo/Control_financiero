import structlog
from fastapi import APIRouter

from app.schemas.predict import PredictRequest, PredictResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
async def predict_category(request: PredictRequest) -> PredictResponse:
    """
    Predice la categoría de una transacción bancaria.

    En la Fase 3.1 devuelve una respuesta stub (sin modelo cargado).
    La Fase 3.2 implementará la inferencia real con DistilBERT.
    """
    logger.info("predict_request", description=request.description[:50], transaction_id=request.transaction_id)

    return PredictResponse(
        category_id=None,
        category_name=None,
        confidence=0.0,
        auto_assigned=False,
        suggested=False,
        model_version="stub",
    )
