from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    transaction_id: int = Field(..., description="ID de la transacción corregida")
    description: str = Field(..., min_length=1, description="Descripción original de la transacción")
    predicted_category_id: int | None = Field(None, description="Categoría que predijo el modelo")
    correct_category_id: int = Field(..., description="Categoría correcta confirmada por el usuario")


class FeedbackResponse(BaseModel):
    status: str
    message: str
    feedback_id: str | None = None
