from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.ml import MLFeedbackRequest, MLFeedbackResponse, MLPredictRequest, MLPredictResponse
from app.services.ml_client import ml_client

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/predict", response_model=MLPredictResponse)
async def predict_category(
    request: MLPredictRequest,
    current_user: User = Depends(get_current_user),
) -> MLPredictResponse:
    """
    Predice la categoría de una transacción usando el modelo ML.

    Devuelve la predicción con su confianza. Si el ml-service no está
    disponible devuelve una respuesta degradada (ml_available=False)
    sin interrumpir el flujo.
    """
    return await ml_client.predict(
        description=request.description,
        transaction_id=request.transaction_id,
    )


@router.post("/feedback", response_model=MLFeedbackResponse)
async def send_feedback(
    request: MLFeedbackRequest,
    current_user: User = Depends(get_current_user),
) -> MLFeedbackResponse:
    """
    Envía feedback sobre una predicción incorrecta para reentrenamiento.

    El usuario confirma o corrige la categoría asignada. El feedback
    se acumula en el ml-service para el ciclo de reentrenamiento.
    """
    return await ml_client.send_feedback(request)


@router.get("/status")
async def get_ml_status(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Devuelve el estado actual del modelo de categorización ML.

    Incluye si el modelo está cargado, su versión, accuracy y
    número de feedbacks pendientes de procesar.
    """
    return await ml_client.get_model_status()
