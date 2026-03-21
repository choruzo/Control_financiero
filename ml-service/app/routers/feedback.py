import uuid

import structlog
from fastapi import APIRouter

from app.schemas.feedback import FeedbackRequest, FeedbackResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def receive_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Recibe feedback del usuario sobre una predicción.

    Almacena la corrección para el reentrenamiento (Fase 3.3).
    En la Fase 3.1 sólo registra el evento en el log.
    """
    feedback_id = str(uuid.uuid4())[:8]
    logger.info(
        "feedback_received",
        feedback_id=feedback_id,
        transaction_id=request.transaction_id,
        predicted=request.predicted_category_id,
        correct=request.correct_category_id,
    )

    return FeedbackResponse(
        status="received",
        message="Feedback registrado. El modelo se entrenará en la próxima ventana de reentrenamiento.",
        feedback_id=feedback_id,
    )
