from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetAlert
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budgets import BudgetCreate, BudgetResponse, BudgetStatusResponse, BudgetUpdate


async def _verify_category_accessible(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            or_(Category.user_id == user_id, Category.is_system.is_(True)),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


async def _get_budget_or_404(
    db: AsyncSession, user_id: uuid.UUID, budget_id: uuid.UUID
) -> Budget:
    result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


async def create_budget(
    db: AsyncSession, user_id: uuid.UUID, data: BudgetCreate
) -> Budget:
    await _verify_category_accessible(db, user_id, data.category_id)

    existing = await db.execute(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == data.category_id,
            Budget.period_year == data.period_year,
            Budget.period_month == data.period_month,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget already exists for this category and period",
        )

    budget = Budget(
        user_id=user_id,
        category_id=data.category_id,
        period_year=data.period_year,
        period_month=data.period_month,
        limit_amount=data.limit_amount,
        alert_threshold=data.alert_threshold,
        name=data.name,
    )
    db.add(budget)
    await db.flush()
    return budget


async def get_budget(
    db: AsyncSession, user_id: uuid.UUID, budget_id: uuid.UUID
) -> Budget:
    return await _get_budget_or_404(db, user_id, budget_id)


async def list_budgets(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_year: int | None = None,
    period_month: int | None = None,
) -> list[Budget]:
    query = select(Budget).where(Budget.user_id == user_id)
    if period_year is not None:
        query = query.where(Budget.period_year == period_year)
    if period_month is not None:
        query = query.where(Budget.period_month == period_month)
    query = query.order_by(
        Budget.period_year.desc(), Budget.period_month.desc(), Budget.created_at.asc()
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_budget(
    db: AsyncSession, user_id: uuid.UUID, budget_id: uuid.UUID, data: BudgetUpdate
) -> Budget:
    budget = await _get_budget_or_404(db, user_id, budget_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(budget, field, value)
    await db.flush()
    return budget


async def delete_budget(
    db: AsyncSession, user_id: uuid.UUID, budget_id: uuid.UUID
) -> None:
    budget = await _get_budget_or_404(db, user_id, budget_id)
    await db.delete(budget)
    await db.flush()


async def get_budget_status(
    db: AsyncSession, user_id: uuid.UUID, budget_id: uuid.UUID
) -> BudgetStatusResponse:
    budget = await _get_budget_or_404(db, user_id, budget_id)

    _, last_day = monthrange(budget.period_year, budget.period_month)
    period_start = date(budget.period_year, budget.period_month, 1)
    period_end = date(budget.period_year, budget.period_month, last_day)

    spent_result = await db.execute(
        select(
            func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0"))
        ).where(
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
    )
    raw_spent = spent_result.scalar_one()
    raw_decimal = Decimal(str(raw_spent)) if raw_spent is not None else Decimal("0")
    spent_amount: Decimal = raw_decimal.quantize(Decimal("0.01"))

    if budget.limit_amount > 0:
        percentage_used = (spent_amount / budget.limit_amount * Decimal("100")).quantize(
            Decimal("0.01")
        )
    else:
        percentage_used = Decimal("0.00")

    is_over_limit = spent_amount > budget.limit_amount
    remaining_amount = budget.limit_amount - spent_amount

    alert_triggered = False
    if percentage_used >= budget.alert_threshold:
        existing_unread = await db.execute(
            select(BudgetAlert).where(
                BudgetAlert.budget_id == budget.id,
                BudgetAlert.is_read.is_(False),
            )
        )
        if existing_unread.scalar_one_or_none() is None:
            new_alert = BudgetAlert(
                budget_id=budget.id,
                spent_amount=spent_amount,
                percentage=percentage_used,
                is_read=False,
            )
            db.add(new_alert)
            await db.flush()
        alert_triggered = True

    return BudgetStatusResponse(
        budget=BudgetResponse.model_validate(budget),
        spent_amount=spent_amount,
        remaining_amount=remaining_amount,
        percentage_used=percentage_used,
        is_over_limit=is_over_limit,
        alert_triggered=alert_triggered,
    )


async def list_budget_statuses(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_year: int,
    period_month: int,
) -> list[BudgetStatusResponse]:
    budgets = await list_budgets(db, user_id, period_year, period_month)
    return [await get_budget_status(db, user_id, b.id) for b in budgets]


async def list_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
) -> list[BudgetAlert]:
    query = (
        select(BudgetAlert)
        .join(Budget, BudgetAlert.budget_id == Budget.id)
        .where(Budget.user_id == user_id)
    )
    if unread_only:
        query = query.where(BudgetAlert.is_read.is_(False))
    query = query.order_by(BudgetAlert.triggered_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def mark_alert_read(
    db: AsyncSession, user_id: uuid.UUID, alert_id: uuid.UUID
) -> BudgetAlert:
    result = await db.execute(
        select(BudgetAlert)
        .join(Budget, BudgetAlert.budget_id == Budget.id)
        .where(BudgetAlert.id == alert_id, Budget.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.is_read = True
    await db.flush()
    return alert
