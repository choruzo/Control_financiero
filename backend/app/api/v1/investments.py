import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.investments import (
    InvestmentCreate,
    InvestmentResponse,
    InvestmentStatusResponse,
    InvestmentSummaryResponse,
    InvestmentUpdate,
)
from app.services import investments as investments_service

router = APIRouter(prefix="/investments", tags=["investments"])


# ── Specific routes BEFORE /{investment_id} to avoid path conflicts ───────────


@router.get("/summary", response_model=InvestmentSummaryResponse)
async def get_investment_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestmentSummaryResponse:
    """Aggregated overview of all active investments."""
    return await investments_service.get_investment_summary(db, current_user.id)


# ── Collection routes ─────────────────────────────────────────────────────────


@router.post("", response_model=InvestmentResponse, status_code=201)
async def create_investment(
    body: InvestmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestmentResponse:
    """Register a new investment (deposit, fund, stock, or bond)."""
    return await investments_service.create_investment(db, current_user.id, body)


@router.get("", response_model=list[InvestmentResponse])
async def list_investments(
    investment_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InvestmentResponse]:
    """List investments with optional filters."""
    return await investments_service.list_investments(
        db, current_user.id, investment_type, is_active
    )


# ── Item routes ───────────────────────────────────────────────────────────────


@router.get("/{investment_id}", response_model=InvestmentResponse)
async def get_investment(
    investment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestmentResponse:
    """Get a single investment by ID."""
    return await investments_service.get_investment(db, current_user.id, investment_id)


@router.get("/{investment_id}/status", response_model=InvestmentStatusResponse)
async def get_investment_status(
    investment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestmentStatusResponse:
    """Get calculated return and status for an investment."""
    return await investments_service.get_investment_status(db, current_user.id, investment_id)


@router.patch("/{investment_id}", response_model=InvestmentResponse)
async def update_investment(
    investment_id: uuid.UUID,
    body: InvestmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestmentResponse:
    """Partially update an investment."""
    return await investments_service.update_investment(db, current_user.id, investment_id, body)


@router.delete("/{investment_id}", status_code=204)
async def delete_investment(
    investment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an investment."""
    await investments_service.delete_investment(db, current_user.id, investment_id)


@router.post("/{investment_id}/renew", response_model=InvestmentResponse)
async def renew_investment(
    investment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestmentResponse:
    """Manually renew a deposit or fund by extending its maturity date."""
    return await investments_service.renew_investment(db, current_user.id, investment_id)
