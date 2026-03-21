from __future__ import annotations

import calendar
import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.investment import Investment
from app.schemas.investments import (
    InvestmentCreate,
    InvestmentResponse,
    InvestmentStatusResponse,
    InvestmentSummaryResponse,
    InvestmentUpdate,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_investment_or_404(
    db: AsyncSession, user_id: uuid.UUID, investment_id: uuid.UUID
) -> Investment:
    result = await db.execute(
        select(Investment).where(
            Investment.id == investment_id, Investment.user_id == user_id
        )
    )
    investment = result.scalar_one_or_none()
    if investment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investment not found")
    return investment


def _calculate_return(
    principal: Decimal,
    annual_rate_pct: Decimal,
    days: int,
    interest_type: str,
    compounding_frequency: str | None,
) -> Decimal:
    """Return accrued interest for the given period.

    Args:
        principal: Initial invested amount.
        annual_rate_pct: Annual rate as percentage (e.g. 4.25 means 4.25%).
        days: Number of days elapsed.
        interest_type: "simple" or "compound".
        compounding_frequency: "annually", "quarterly", or "monthly" (compound only).
    """
    if days <= 0 or annual_rate_pct <= 0:
        return Decimal("0.00")

    rate = annual_rate_pct / Decimal("100")
    t = Decimal(str(days)) / Decimal("365")

    if interest_type == "simple":
        interest = principal * rate * t
    else:
        # Compounding periods per year
        n_map = {"annually": Decimal("1"), "quarterly": Decimal("4"), "monthly": Decimal("12")}
        n = n_map.get(compounding_frequency or "annually", Decimal("1"))
        interest = principal * ((1 + rate / n) ** (n * t)) - principal  # type: ignore[operator]

    return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def create_investment(
    db: AsyncSession, user_id: uuid.UUID, data: InvestmentCreate
) -> Investment:
    if data.account_id is not None:
        acc_result = await db.execute(
            select(Account).where(
                Account.id == data.account_id, Account.user_id == user_id
            )
        )
        if acc_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
            )

    investment = Investment(
        user_id=user_id,
        account_id=data.account_id,
        name=data.name,
        investment_type=data.investment_type,
        principal_amount=data.principal_amount,
        interest_rate=data.interest_rate,
        interest_type=data.interest_type,
        compounding_frequency=data.compounding_frequency,
        current_value=data.current_value,
        start_date=data.start_date,
        maturity_date=data.maturity_date,
        auto_renew=data.auto_renew,
        renewal_period_months=data.renewal_period_months,
        notes=data.notes,
    )
    db.add(investment)
    await db.flush()
    return investment


async def get_investment(
    db: AsyncSession, user_id: uuid.UUID, investment_id: uuid.UUID
) -> Investment:
    return await _get_investment_or_404(db, user_id, investment_id)


async def list_investments(
    db: AsyncSession,
    user_id: uuid.UUID,
    investment_type: str | None = None,
    is_active: bool | None = None,
) -> list[Investment]:
    query = select(Investment).where(Investment.user_id == user_id)
    if investment_type is not None:
        query = query.where(Investment.investment_type == investment_type)
    if is_active is not None:
        query = query.where(Investment.is_active == is_active)
    query = query.order_by(Investment.start_date.desc(), Investment.created_at.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_investment(
    db: AsyncSession,
    user_id: uuid.UUID,
    investment_id: uuid.UUID,
    data: InvestmentUpdate,
) -> Investment:
    investment = await _get_investment_or_404(db, user_id, investment_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(investment, field, value)
    await db.flush()
    return investment


async def delete_investment(
    db: AsyncSession, user_id: uuid.UUID, investment_id: uuid.UUID
) -> None:
    investment = await _get_investment_or_404(db, user_id, investment_id)
    await db.delete(investment)
    await db.flush()


# ── Business Logic ────────────────────────────────────────────────────────────


async def get_investment_status(
    db: AsyncSession, user_id: uuid.UUID, investment_id: uuid.UUID
) -> InvestmentStatusResponse:
    investment = await _get_investment_or_404(db, user_id, investment_id)

    today = datetime.now(UTC).date()
    days_held = (today - investment.start_date).days

    accrued_interest = _calculate_return(
        principal=investment.principal_amount,
        annual_rate_pct=investment.interest_rate,
        days=days_held,
        interest_type=investment.interest_type,
        compounding_frequency=investment.compounding_frequency,
    )

    # Use manually set current_value if available, otherwise derive from interest formula
    if investment.current_value is not None:
        effective_value = investment.current_value
        total_return = (effective_value - investment.principal_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        effective_value = investment.principal_amount + accrued_interest
        total_return = accrued_interest

    if investment.principal_amount > 0:
        return_percentage = (
            total_return / investment.principal_amount * Decimal("100")
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    else:
        return_percentage = Decimal("0.0000")

    days_to_maturity: int | None = None
    if investment.maturity_date is not None:
        days_to_maturity = (investment.maturity_date - today).days

    return InvestmentStatusResponse(
        investment=InvestmentResponse.model_validate(investment),
        accrued_interest=accrued_interest,
        total_return=total_return,
        return_percentage=return_percentage,
        days_held=days_held,
        days_to_maturity=days_to_maturity,
    )


async def renew_investment(
    db: AsyncSession, user_id: uuid.UUID, investment_id: uuid.UUID
) -> Investment:
    investment = await _get_investment_or_404(db, user_id, investment_id)

    if investment.maturity_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot renew an investment without a maturity date",
        )
    if investment.renewal_period_months is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="renewal_period_months must be set to renew the investment",
        )

    # Extend maturity_date by renewal_period_months months
    current_maturity = investment.maturity_date
    month = current_maturity.month - 1 + investment.renewal_period_months
    year = current_maturity.year + month // 12
    month = month % 12 + 1
    # Clamp day to last valid day of the target month
    max_day = calendar.monthrange(year, month)[1]
    new_day = min(current_maturity.day, max_day)
    investment.maturity_date = date(year, month, new_day)
    investment.renewals_count += 1
    await db.flush()
    return investment


async def get_investment_summary(
    db: AsyncSession, user_id: uuid.UUID
) -> InvestmentSummaryResponse:
    today = datetime.now(UTC).date()
    result = await db.execute(
        select(Investment).where(
            Investment.user_id == user_id, Investment.is_active.is_(True)
        )
    )
    investments = list(result.scalars().all())

    total_principal = Decimal("0.00")
    total_current_value = Decimal("0.00")
    total_return = Decimal("0.00")
    by_type: dict[str, int] = {}
    return_percentages: list[Decimal] = []

    for inv in investments:
        by_type[inv.investment_type] = by_type.get(inv.investment_type, 0) + 1
        total_principal += inv.principal_amount

        days_held = (today - inv.start_date).days
        accrued = _calculate_return(
            principal=inv.principal_amount,
            annual_rate_pct=inv.interest_rate,
            days=days_held,
            interest_type=inv.interest_type,
            compounding_frequency=inv.compounding_frequency,
        )

        if inv.current_value is not None:
            effective = inv.current_value
            ret = (effective - inv.principal_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            effective = inv.principal_amount + accrued
            ret = accrued

        total_current_value += effective
        total_return += ret

        if inv.principal_amount > 0:
            return_percentages.append(
                (ret / inv.principal_amount * Decimal("100")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
            )

    if return_percentages:
        avg_return_pct = (
            sum(return_percentages, Decimal("0")) / Decimal(str(len(return_percentages)))
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    else:
        avg_return_pct = Decimal("0.0000")

    return InvestmentSummaryResponse(
        total_investments=len(investments),
        total_principal=total_principal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total_current_value=total_current_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total_return=total_return.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        average_return_percentage=avg_return_pct,
        by_type=by_type,
    )
