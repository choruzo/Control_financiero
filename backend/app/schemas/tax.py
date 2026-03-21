from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TaxBracketResponse(BaseModel):
    id: uuid.UUID
    tax_year: int
    bracket_type: str
    min_amount: Decimal
    max_amount: Decimal | None
    rate: Decimal

    model_config = {"from_attributes": True}


class TaxConfigCreate(BaseModel):
    tax_year: int = Field(..., ge=2020, le=2030)
    gross_annual_salary: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)


class TaxConfigUpdate(BaseModel):
    gross_annual_salary: Decimal | None = Field(None, gt=Decimal("0"), decimal_places=2)


class TaxConfigResponse(BaseModel):
    id: uuid.UUID
    tax_year: int
    gross_annual_salary: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BracketBreakdown(BaseModel):
    rate: Decimal
    taxable_in_bracket: Decimal
    tax_in_bracket: Decimal


class TaxCalculationResponse(BaseModel):
    tax_year: int
    gross_annual: Decimal
    ss_annual: Decimal
    ss_rate: Decimal
    work_expenses_deduction: Decimal
    taxable_base: Decimal
    irpf_annual: Decimal
    effective_rate: Decimal
    net_annual: Decimal
    net_monthly: Decimal
    bracket_breakdown: list[BracketBreakdown]
