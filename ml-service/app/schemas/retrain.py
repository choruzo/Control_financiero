from pydantic import BaseModel, Field


class RetrainResponse(BaseModel):
    status: str = Field(
        description="Estado del disparo: 'started', 'skipped', 'in_progress', 'error'"
    )
    feedback_count: int = Field(0, description="Número de feedbacks disponibles en Redis")
    reason: str | None = Field(None, description="Motivo cuando status es 'skipped' o 'error'")
    model_version: str | None = Field(None, description="Versión del modelo activo al iniciar")
