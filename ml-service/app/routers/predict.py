import structlog
from fastapi import APIRouter, Request

from app.config import settings
from app.ml.categories import LABEL_TO_INDEX
from app.ml.model_manager import ModelManager
from app.schemas.predict import PredictRequest, PredictResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
async def predict_category(request: PredictRequest, req: Request) -> PredictResponse:
    """
    Predice la categoría de una transacción bancaria usando DistilBERT.

    - Si confianza >= auto_assign_threshold (0.85): auto_assigned=True
    - Si confianza >= suggest_threshold (0.5): suggested=True
    - Si el modelo no está cargado: devuelve confianza 0.0 en modo degradado
    """
    manager: ModelManager = req.app.state.model_manager

    logger.info(
        "predict_request",
        description=request.description[:50],
        transaction_id=request.transaction_id,
        model_loaded=manager.loaded,
    )

    category_name, confidence = manager.predict(request.description)
    category_id = LABEL_TO_INDEX.get(category_name)

    auto_assigned = confidence >= settings.categorization_threshold
    suggested = not auto_assigned and confidence >= settings.categorization_suggest_threshold
    model_version = manager.metadata.get("version", "degraded") if manager.loaded else "degraded"

    return PredictResponse(
        category_id=category_id,
        category_name=category_name if confidence > 0.0 else None,
        confidence=confidence,
        auto_assigned=auto_assigned,
        suggested=suggested,
        model_version=model_version,
    )
