from datetime import datetime

from pydantic import BaseModel, Field


class ModelStatusResponse(BaseModel):
    loaded: bool = Field(False, description="True si el modelo está cargado en memoria")
    version: str | None = Field(None, description="Versión del modelo activo")
    accuracy: float | None = Field(None, description="Accuracy en el conjunto de validación")
    last_trained: datetime | None = Field(None, description="Fecha del último entrenamiento")
    feedback_count: int = Field(0, description="Número de feedbacks almacenados para reentrenamiento")
