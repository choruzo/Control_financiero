from pydantic import BaseModel, Field


class MLPredictRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Descripción de la transacción")
    transaction_id: int | None = Field(None, description="ID de la transacción")


class MLPredictResponse(BaseModel):
    category_id: int | None = Field(None, description="ID de categoría predicha")
    category_name: str | None = Field(None, description="Nombre de categoría predicha")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confianza de la predicción")
    auto_assigned: bool = Field(False, description="True si confianza > umbral de auto-asignación")
    suggested: bool = Field(False, description="True si confianza > umbral de sugerencia")
    model_version: str = Field("stub", description="Versión del modelo usado")
    ml_available: bool = Field(True, description="False si el ml-service no está disponible")


class MLFeedbackRequest(BaseModel):
    transaction_id: int = Field(..., description="ID de la transacción corregida")
    description: str = Field(..., min_length=1, description="Descripción original de la transacción")
    predicted_category_id: int | None = Field(None, description="Categoría que predijo el modelo")
    correct_category_id: int = Field(..., description="Categoría correcta confirmada por el usuario")


class MLFeedbackResponse(BaseModel):
    status: str
    message: str
    feedback_id: str | None = None
    ml_available: bool = True


# ---------------------------------------------------------------------------
# Forecast (Fase 4.1)
# ---------------------------------------------------------------------------


class MLForecastPoint(BaseModel):
    year: int
    month: int
    income_p10: float
    income_p50: float
    income_p90: float
    expenses_p10: float
    expenses_p50: float
    expenses_p90: float
    net_p10: float
    net_p50: float
    net_p90: float


class MLForecastRequest(BaseModel):
    historical_data: list[dict] = Field(
        ..., description="Lista de {year, month, income, expenses} en orden cronológico"
    )
    months_ahead: int = Field(default=6, ge=1, le=12)
    include_intervals: bool = True


class MLForecastResponse(BaseModel):
    predictions: list[MLForecastPoint]
    model_used: str
    model_version: str
    data_months_provided: int
    ml_available: bool = True
