"""Router de escenarios "what-if" (Fase 4.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.scenarios import ScenarioRequest, ScenarioResponse
from app.services import scenarios as scenarios_svc

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/analyze", response_model=ScenarioResponse)
async def analyze_scenario(
    body: ScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioResponse:
    """Motor de escenarios "what-if".

    Simula el impacto de cambios paramétricos sobre el cashflow futuro:
    - Variación de sueldo (±X%)
    - Variación del Euríbor (si hay simulación hipotecaria guardada)
    - Añadir/eliminar gastos recurrentes
    - Impacto fiscal IRPF (si se proporciona gross_annual)

    Devuelve distribución de resultados P10/P50/P90 via Monte Carlo.
    """
    return await scenarios_svc.analyze_scenario(db, current_user.id, body)
