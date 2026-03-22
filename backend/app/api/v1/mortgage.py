import uuid
from decimal import Decimal  # noqa: I001

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.mortgage import (
    AffordabilityResponse,
    AIAffordabilityResponse,
    MortgageCompareRequest,
    MortgageCompareResponse,
    MortgageSaveRequest,
    MortgageSimulateRequest,
    MortgageSimulationResponse,
    MortgageSimulationResult,
)
from app.services import mortgage as mortgage_service

router = APIRouter(prefix="/mortgage", tags=["mortgage"])


# ── Stateless calculation endpoints ───────────────────────────────────────────


@router.post("/simulate", response_model=MortgageSimulationResult)
async def simulate_mortgage(
    body: MortgageSimulateRequest,
    current_user: User = Depends(get_current_user),
) -> MortgageSimulationResult:
    """Calculate mortgage payments and amortization schedule without saving.

    Supports fixed, variable (Euríbor + spread) and mixed rate types.
    Returns the full amortization table and optional closing costs.
    """
    return await mortgage_service.simulate_mortgage(body)


@router.post("/compare", response_model=MortgageCompareResponse)
async def compare_scenarios(
    body: MortgageCompareRequest,
    current_user: User = Depends(get_current_user),
) -> MortgageCompareResponse:
    """Compare 2–5 mortgage scenarios (e.g. fixed vs variable vs mixed) side by side."""
    return await mortgage_service.compare_scenarios(body)


@router.get("/affordability", response_model=AffordabilityResponse)
async def get_affordability(
    tax_config_id: uuid.UUID | None = Query(
        None,
        description="If provided, use net monthly salary from this tax config instead of "
        "transaction-derived income.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AffordabilityResponse:
    """Estimate the maximum mortgage amount based on the user's income.

    By default uses the last 3 months of income transactions to compute average
    monthly net income. Pass *tax_config_id* to use the calculated net salary
    from a saved tax configuration instead (more accurate for salaried workers).
    """
    return await mortgage_service.get_affordability(db, current_user.id, tax_config_id)


@router.get("/ai-affordability", response_model=AIAffordabilityResponse)
async def get_ai_affordability(
    months_ahead: int = Query(
        default=12,
        ge=6,
        le=24,
        description="Horizonte de predicción en meses (6-24).",
    ),
    term_years: int = Query(
        default=25,
        ge=5,
        le=40,
        description="Plazo hipotecario en años para los cálculos de capacidad.",
    ),
    tax_config_id: uuid.UUID | None = Query(
        None,
        description="Si se provee, usa el salario neto de este TaxConfig en vez del histórico.",
    ),
    gross_annual: Decimal | None = Query(
        None,
        gt=0,
        description="Bruto anual alternativo para el cálculo IRPF (sin TaxConfig guardado).",
    ),
    euribor_stress_levels: list[float] = Query(
        default=[0, 1, 2, 3],
        description="Incrementos de Euríbor sobre el nivel base para los stress tests.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AIAffordabilityResponse:
    """AI-powered mortgage affordability based on forecasted future income.

    Combines ML cashflow predictions (LSTM/Prophet) with stress tests at
    multiple Euríbor levels to answer: "How much mortgage can I afford in
    X months, even if rates rise to Y%?"

    Returns:
    - Forecasted income percentiles (P10/P50/P90) over the prediction horizon
    - Max affordable loan at each Euríbor stress level
    - Comparison with current affordability (last 3 months of actual income)
    """
    return await mortgage_service.get_ai_affordability(
        db=db,
        user_id=current_user.id,
        months_ahead=months_ahead,
        term_years=term_years,
        tax_config_id=tax_config_id,
        gross_annual=gross_annual,
        euribor_stress_levels=[Decimal(str(lvl)) for lvl in euribor_stress_levels],
    )


# ── Saved simulations CRUD ────────────────────────────────────────────────────


@router.post(
    "/simulations",
    response_model=MortgageSimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_simulation(
    body: MortgageSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MortgageSimulationResponse:
    """Calculate and save a named mortgage simulation for later reference."""
    return await mortgage_service.save_simulation(db, current_user.id, body)


@router.get("/simulations", response_model=list[MortgageSimulationResponse])
async def list_simulations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MortgageSimulationResponse]:
    """List all saved mortgage simulations for the current user."""
    return await mortgage_service.list_simulations(db, current_user.id)


@router.get("/simulations/{sim_id}", response_model=MortgageSimulationResponse)
async def get_simulation(
    sim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MortgageSimulationResponse:
    """Retrieve a specific saved simulation by ID."""
    return await mortgage_service.get_simulation(db, current_user.id, sim_id)


@router.delete("/simulations/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_simulation(
    sim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a saved simulation."""
    await mortgage_service.delete_simulation(db, current_user.id, sim_id)
