from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Descripción de la transacción bancaria")
    transaction_id: int | None = Field(None, description="ID de la transacción en el backend")


class PredictResponse(BaseModel):
    category_id: int | None = Field(None, description="ID de categoría predicha (None si sin modelo)")
    category_name: str | None = Field(None, description="Nombre de categoría predicha")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confianza de la predicción")
    auto_assigned: bool = Field(False, description="True si confianza > umbral de auto-asignación")
    suggested: bool = Field(False, description="True si confianza > umbral de sugerencia")
    model_version: str = Field("stub", description="Versión del modelo usado")
