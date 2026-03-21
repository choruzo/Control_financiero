import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    period_year: int = Field(..., ge=2000, le=2100)
    period_month: int = Field(..., ge=1, le=12)
    limit_amount: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)
    alert_threshold: Decimal = Field(
        Decimal("80.00"), ge=Decimal("0"), le=Decimal("100"), decimal_places=2
    )
    name: str | None = Field(None, min_length=1, max_length=100)


class BudgetUpdate(BaseModel):
    limit_amount: Decimal | None = Field(None, gt=Decimal("0"), decimal_places=2)
    alert_threshold: Decimal | None = Field(
        None, ge=Decimal("0"), le=Decimal("100"), decimal_places=2
    )
    name: str | None = Field(None, min_length=1, max_length=100)


class BudgetResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID
    period_year: int
    period_month: int
    limit_amount: Decimal
    alert_threshold: Decimal
    name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BudgetStatusResponse(BaseModel):
    budget: BudgetResponse
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: Decimal
    is_over_limit: bool
    alert_triggered: bool


class BudgetAlertResponse(BaseModel):
    id: uuid.UUID
    budget_id: uuid.UUID
    triggered_at: datetime
    spent_amount: Decimal
    percentage: Decimal
    is_read: bool

    model_config = {"from_attributes": True}
