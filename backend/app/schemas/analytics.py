from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    year: int
    month: int
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    savings_rate: Decimal
    total_balance: Decimal
    transaction_count: int


class CashflowMonthResponse(BaseModel):
    year: int
    month: int
    total_income: Decimal
    total_expenses: Decimal
    net: Decimal


class CategoryExpenseResponse(BaseModel):
    category_id: uuid.UUID | None
    category_name: str
    total_amount: Decimal
    transaction_count: int
    percentage: Decimal


class SavingsRateMonthResponse(BaseModel):
    year: int
    month: int
    income: Decimal
    expenses: Decimal
    net_savings: Decimal
    savings_rate: Decimal
    moving_avg_3m: Decimal | None
    moving_avg_6m: Decimal | None


class TrendsResponse(BaseModel):
    year: int
    month: int
    income: Decimal
    expenses: Decimal
    net_savings: Decimal
    income_change_pct: Decimal | None
    expenses_change_pct: Decimal | None
    savings_change_pct: Decimal | None
    income_vs_avg_pct: Decimal | None
    expenses_vs_avg_pct: Decimal | None
    savings_vs_avg_pct: Decimal | None
