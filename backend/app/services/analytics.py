from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.analytics import (
    CashflowMonthResponse,
    CategoryExpenseResponse,
    OverviewResponse,
    SavingsRateMonthResponse,
    TrendsResponse,
)

_TWO = Decimal("0.01")
_HUNDRED = Decimal("100")


def _q(value: Decimal | None) -> Decimal:
    """Quantize a Decimal to 2 decimal places, treating None as 0."""
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(_TWO, rounding=ROUND_HALF_UP)


def _pct_change(current: Decimal, previous: Decimal) -> Decimal | None:
    """Percentage change from previous to current. Returns None when previous is zero."""
    if previous == 0:
        return None
    return ((current - previous) / abs(previous) * _HUNDRED).quantize(
        _TWO, rounding=ROUND_HALF_UP
    )


def _months_window(year: int, month: int, n: int) -> list[tuple[int, int]]:
    """Return list of (year, month) for the N months ending at (year, month), oldest first."""
    months: list[tuple[int, int]] = []
    y, m = year, month
    for _ in range(n):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


async def _month_summary(
    db: AsyncSession, user_id: uuid.UUID, year: int, month: int
) -> tuple[Decimal, Decimal, int]:
    """Return (income, expenses, transaction_count) for a given month."""
    _, last_day = monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, last_day)

    result = await db.execute(
        select(
            Transaction.transaction_type,
            func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0")).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type.in_(["income", "expense"]),
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
        .group_by(Transaction.transaction_type)
    )
    rows = result.all()

    income = Decimal("0.00")
    expenses = Decimal("0.00")
    count = 0
    for row in rows:
        if row.transaction_type == "income":
            income = _q(row.total)
            count += row.cnt
        elif row.transaction_type == "expense":
            expenses = _q(row.total)
            count += row.cnt
    return income, expenses, count


async def get_overview(
    db: AsyncSession, user_id: uuid.UUID, year: int, month: int
) -> OverviewResponse:
    income, expenses, count = await _month_summary(db, user_id, year, month)
    net_savings = _q(income - expenses)

    savings_rate = Decimal("0.00")
    if income > 0:
        savings_rate = _q(net_savings / income * _HUNDRED)

    balance_result = await db.execute(
        select(func.coalesce(func.sum(Account.balance), Decimal("0"))).where(
            Account.user_id == user_id,
            Account.is_active.is_(True),
        )
    )
    total_balance = _q(balance_result.scalar_one())

    return OverviewResponse(
        year=year,
        month=month,
        total_income=income,
        total_expenses=expenses,
        net_savings=net_savings,
        savings_rate=savings_rate,
        total_balance=total_balance,
        transaction_count=count,
    )


async def get_cashflow(
    db: AsyncSession, user_id: uuid.UUID, months: int
) -> list[CashflowMonthResponse]:
    today = datetime.now(UTC).date()
    period_months = _months_window(today.year, today.month, months)

    start_year, start_month = period_months[0]
    _, last_day = monthrange(today.year, today.month)
    period_start = date(start_year, start_month, 1)
    period_end = date(today.year, today.month, last_day)

    result = await db.execute(
        select(
            extract("year", Transaction.date).label("yr"),
            extract("month", Transaction.date).label("mo"),
            Transaction.transaction_type,
            func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0")).label("total"),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type.in_(["income", "expense"]),
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
        .group_by(
            extract("year", Transaction.date),
            extract("month", Transaction.date),
            Transaction.transaction_type,
        )
    )
    rows = result.all()

    data: dict[tuple[int, int, str], Decimal] = {}
    for row in rows:
        key = (int(row.yr), int(row.mo), row.transaction_type)
        data[key] = _q(row.total)

    result_list: list[CashflowMonthResponse] = []
    for y, m in period_months:
        inc = data.get((y, m, "income"), Decimal("0.00"))
        exp = data.get((y, m, "expense"), Decimal("0.00"))
        result_list.append(
            CashflowMonthResponse(
                year=y,
                month=m,
                total_income=inc,
                total_expenses=exp,
                net=_q(inc - exp),
            )
        )
    return result_list


async def get_expenses_by_category(
    db: AsyncSession, user_id: uuid.UUID, year: int, month: int
) -> list[CategoryExpenseResponse]:
    _, last_day = monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, last_day)

    result = await db.execute(
        select(
            Transaction.category_id,
            Category.name.label("category_name"),
            func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0")).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
        .group_by(Transaction.category_id, Category.name)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
    )
    rows = result.all()

    if not rows:
        return []

    total_expenses = sum(_q(r.total) for r in rows)

    items: list[CategoryExpenseResponse] = []
    for row in rows:
        amount = _q(row.total)
        pct = (
            _q(amount / total_expenses * _HUNDRED) if total_expenses > 0 else Decimal("0.00")
        )
        items.append(
            CategoryExpenseResponse(
                category_id=row.category_id,
                category_name=row.category_name or "Sin categoría",
                total_amount=amount,
                transaction_count=row.cnt,
                percentage=pct,
            )
        )
    return items


async def get_savings_rate(
    db: AsyncSession, user_id: uuid.UUID, months: int
) -> list[SavingsRateMonthResponse]:
    today = datetime.now(UTC).date()
    period_months = _months_window(today.year, today.month, months)

    monthly: list[tuple[int, int, Decimal, Decimal]] = []
    for y, m in period_months:
        income, expenses, _ = await _month_summary(db, user_id, y, m)
        monthly.append((y, m, income, expenses))

    result_list: list[SavingsRateMonthResponse] = []
    savings_rates: list[Decimal] = []

    for i, (y, m, income, expenses) in enumerate(monthly):
        net = _q(income - expenses)
        rate = _q(net / income * _HUNDRED) if income > 0 else Decimal("0.00")
        savings_rates.append(rate)

        avg_3m: Decimal | None = None
        avg_6m: Decimal | None = None
        if i >= 2:
            avg_3m = _q(sum(savings_rates[i - 2 : i + 1]) / 3)
        if i >= 5:
            avg_6m = _q(sum(savings_rates[i - 5 : i + 1]) / 6)

        result_list.append(
            SavingsRateMonthResponse(
                year=y,
                month=m,
                income=income,
                expenses=expenses,
                net_savings=net,
                savings_rate=rate,
                moving_avg_3m=avg_3m,
                moving_avg_6m=avg_6m,
            )
        )
    return result_list


async def get_trends(
    db: AsyncSession, user_id: uuid.UUID, year: int, month: int
) -> TrendsResponse:
    income, expenses, _ = await _month_summary(db, user_id, year, month)
    net_savings = _q(income - expenses)

    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    prev_income, prev_expenses, _ = await _month_summary(db, user_id, prev_y, prev_m)
    prev_net = _q(prev_income - prev_expenses)

    # Last 12 months ending at prev_month (excluding current month)
    avg_months = _months_window(prev_y, prev_m, 12)
    avg_incomes: list[Decimal] = []
    avg_exps: list[Decimal] = []
    avg_nets: list[Decimal] = []
    for ay, am in avg_months:
        ai, ae, _ = await _month_summary(db, user_id, ay, am)
        avg_incomes.append(ai)
        avg_exps.append(ae)
        avg_nets.append(_q(ai - ae))

    avg_income = _q(sum(avg_incomes) / len(avg_incomes))
    avg_exp = _q(sum(avg_exps) / len(avg_exps))
    avg_net = _q(sum(avg_nets) / len(avg_nets))

    return TrendsResponse(
        year=year,
        month=month,
        income=income,
        expenses=expenses,
        net_savings=net_savings,
        income_change_pct=_pct_change(income, prev_income),
        expenses_change_pct=_pct_change(expenses, prev_expenses),
        savings_change_pct=_pct_change(net_savings, prev_net),
        income_vs_avg_pct=_pct_change(income, avg_income),
        expenses_vs_avg_pct=_pct_change(expenses, avg_exp),
        savings_vs_avg_pct=_pct_change(net_savings, avg_net),
    )
