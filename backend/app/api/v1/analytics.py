from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    CashflowMonthResponse,
    CategoryExpenseResponse,
    OverviewResponse,
    SavingsRateMonthResponse,
    TrendsResponse,
)
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _current_year_month() -> tuple[int, int]:
    today = datetime.now(UTC).date()
    return today.year, today.month


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OverviewResponse:
    """Monthly financial summary: income, expenses, savings, and total account balance."""
    y, m = _current_year_month()
    return await analytics_service.get_overview(
        db, current_user.id, year or y, month or m
    )


@router.get("/cashflow", response_model=list[CashflowMonthResponse])
async def get_cashflow(
    months: Annotated[int, Query(ge=1, le=60)] = 12,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CashflowMonthResponse]:
    """Monthly cash flow for the last N months (default 12, max 60)."""
    return await analytics_service.get_cashflow(db, current_user.id, months)


@router.get("/expenses-by-category", response_model=list[CategoryExpenseResponse])
async def get_expenses_by_category(
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryExpenseResponse]:
    """Expenses grouped by category for a given month."""
    y, m = _current_year_month()
    return await analytics_service.get_expenses_by_category(
        db, current_user.id, year or y, month or m
    )


@router.get("/savings-rate", response_model=list[SavingsRateMonthResponse])
async def get_savings_rate(
    months: Annotated[int, Query(ge=1, le=60)] = 12,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SavingsRateMonthResponse]:
    """Monthly savings rate and moving averages for the last N months."""
    return await analytics_service.get_savings_rate(db, current_user.id, months)


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrendsResponse:
    """Trends for a given month: changes vs previous month and vs 12-month average."""
    y, m = _current_year_month()
    return await analytics_service.get_trends(
        db, current_user.id, year or y, month or m
    )
