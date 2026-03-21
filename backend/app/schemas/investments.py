import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

INVESTMENT_TYPES = Literal["deposit", "fund", "stock", "bond"]
INTEREST_TYPES = Literal["simple", "compound"]
COMPOUNDING_FREQUENCIES = Literal["annually", "quarterly", "monthly"]


class InvestmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    investment_type: INVESTMENT_TYPES
    principal_amount: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)
    interest_rate: Decimal = Field(..., ge=Decimal("0"), decimal_places=4)
    interest_type: INTEREST_TYPES
    compounding_frequency: COMPOUNDING_FREQUENCIES | None = None
    start_date: date
    maturity_date: date | None = None
    auto_renew: bool = False
    renewal_period_months: int | None = Field(None, ge=1, le=360)
    current_value: Decimal | None = Field(None, gt=Decimal("0"), decimal_places=2)
    account_id: uuid.UUID | None = None
    notes: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_compound_frequency(self) -> "InvestmentCreate":
        if self.interest_type == "compound" and self.compounding_frequency is None:
            raise ValueError("compounding_frequency is required when interest_type is 'compound'")
        if self.interest_type == "simple" and self.compounding_frequency is not None:
            raise ValueError(
                "compounding_frequency must be null when interest_type is 'simple'"
            )
        if self.maturity_date is not None and self.maturity_date <= self.start_date:
            raise ValueError("maturity_date must be after start_date")
        if self.auto_renew and self.renewal_period_months is None:
            raise ValueError("renewal_period_months is required when auto_renew is true")
        return self


class InvestmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    interest_rate: Decimal | None = Field(None, ge=Decimal("0"), decimal_places=4)
    maturity_date: date | None = None
    auto_renew: bool | None = None
    renewal_period_months: int | None = Field(None, ge=1, le=360)
    current_value: Decimal | None = Field(None, gt=Decimal("0"), decimal_places=2)
    notes: str | None = Field(None, max_length=1000)
    is_active: bool | None = None


class InvestmentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID | None
    name: str
    investment_type: str
    principal_amount: Decimal
    interest_rate: Decimal
    interest_type: str
    compounding_frequency: str | None
    current_value: Decimal | None
    start_date: date
    maturity_date: date | None
    auto_renew: bool
    renewal_period_months: int | None
    renewals_count: int
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvestmentStatusResponse(BaseModel):
    investment: InvestmentResponse
    accrued_interest: Decimal
    total_return: Decimal
    return_percentage: Decimal
    days_held: int
    days_to_maturity: int | None


class InvestmentSummaryResponse(BaseModel):
    total_investments: int
    total_principal: Decimal
    total_current_value: Decimal
    total_return: Decimal
    average_return_percentage: Decimal
    by_type: dict[str, int]
