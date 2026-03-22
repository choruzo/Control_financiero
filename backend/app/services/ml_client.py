import structlog
import httpx

from app.config import settings
from app.schemas.ml import MLFeedbackRequest, MLFeedbackResponse, MLPredictRequest, MLPredictResponse

logger = structlog.get_logger(__name__)

_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


class MLClient:
    """Cliente async para comunicación HTTP con el microservicio ML."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or settings.ml_service_url

    async def predict(
        self,
        description: str,
        transaction_id: int | None = None,
    ) -> MLPredictResponse:
        """
        Solicita la predicción de categoría para una transacción.

        Si el ml-service no está disponible devuelve una respuesta degradada
        en lugar de lanzar una excepción, para no interrumpir el flujo principal.
        """
        payload = MLPredictRequest(description=description, transaction_id=transaction_id)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{self._base_url}/predict",
                    json=payload.model_dump(),
                )
                response.raise_for_status()
                data = response.json()
                return MLPredictResponse(**data, ml_available=True)
        except httpx.TimeoutException:
            logger.warning("ml_client_timeout", url=self._base_url)
            return self._unavailable_predict_response()
        except httpx.HTTPStatusError as exc:
            logger.warning("ml_client_http_error", status=exc.response.status_code, url=self._base_url)
            return self._unavailable_predict_response()
        except httpx.RequestError as exc:
            logger.warning("ml_client_connection_error", error=str(exc), url=self._base_url)
            return self._unavailable_predict_response()

    async def send_feedback(self, request: MLFeedbackRequest) -> MLFeedbackResponse:
        """
        Envía feedback del usuario al ml-service para reentrenamiento.

        Si el ml-service no está disponible registra el error y devuelve
        una respuesta degradada.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{self._base_url}/feedback",
                    json=request.model_dump(),
                )
                response.raise_for_status()
                data = response.json()
                return MLFeedbackResponse(**data, ml_available=True)
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning("ml_client_feedback_error", error=str(exc), url=self._base_url)
            return MLFeedbackResponse(
                status="queued",
                message="ML service no disponible. El feedback se procesará cuando el servicio esté activo.",
                ml_available=False,
            )

    async def get_model_status(self) -> dict:
        """Devuelve el estado del modelo ML. Si no disponible, indica que está offline."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(f"{self._base_url}/model/status")
                response.raise_for_status()
                return {**response.json(), "ml_available": True}
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning("ml_client_status_error", error=str(exc), url=self._base_url)
            return {
                "loaded": False,
                "version": None,
                "accuracy": None,
                "last_trained": None,
                "feedback_count": 0,
                "ml_available": False,
            }

    def trigger_retrain_sync(self) -> dict:
        """
        Dispara el reentrenamiento incremental del ml-service (llamada síncrona).

        Diseñado para uso desde Celery tasks, que no corren en un asyncio event loop.
        Siempre devuelve un dict con 'status' y 'ml_available'; nunca lanza excepción.
        """
        try:
            with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                response = client.post(f"{self._base_url}/retrain")
                response.raise_for_status()
                return {**response.json(), "ml_available": True}
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning("ml_client_retrain_sync_error", error=str(exc), url=self._base_url)
            return {"status": "error", "ml_available": False, "reason": str(exc)}

    async def health_check(self) -> bool:
        """Retorna True si el ml-service responde correctamente."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(f"{self._base_url}/health")
                return response.status_code == 200
        except (httpx.TimeoutException, httpx.RequestError):
            return False

    @staticmethod
    def _unavailable_predict_response() -> MLPredictResponse:
        return MLPredictResponse(
            category_id=None,
            category_name=None,
            confidence=0.0,
            auto_assigned=False,
            suggested=False,
            model_version="unavailable",
            ml_available=False,
        )


ml_client = MLClient()
