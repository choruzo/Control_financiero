import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.mortgage import (
    AffordabilityResponse,
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
