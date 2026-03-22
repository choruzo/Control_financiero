from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── Literals ──────────────────────────────────────────────────────────────────

RATE_TYPES = Literal["fixed", "variable", "mixed"]
PROPERTY_TYPES = Literal["new", "second_hand"]
REVIEW_FREQUENCIES = Literal["annual", "semiannual"]


# ── Amortization schedule ─────────────────────────────────────────────────────


class AmortizationRowSchema(BaseModel):
    month: int
    payment: Decimal
    principal: Decimal
    interest: Decimal
    balance: Decimal
    applied_rate: Decimal  # annual rate applied this month


# ── Closing costs ─────────────────────────────────────────────────────────────


class ClosingCostsSchema(BaseModel):
    notary: Decimal
    registry: Decimal
    tax: Decimal       # ITP or AJD depending on property_type
    gestor: Decimal
    appraisal: Decimal
    total: Decimal


# ── Simulate ──────────────────────────────────────────────────────────────────


class MortgageSimulateRequest(BaseModel):
    property_price: Decimal = Field(..., gt=0, decimal_places=2)
    down_payment: Decimal = Field(..., gt=0, decimal_places=2)
    rate_type: RATE_TYPES
    term_years: int = Field(..., ge=5, le=40)

    # Fixed / mixed-fixed period rate
    interest_rate: Decimal | None = Field(None, ge=0, decimal_places=4)

    # Variable / mixed-variable parameters
    euribor_rate: Decimal | None = Field(None, decimal_places=4)
    spread: Decimal | None = Field(None, ge=0, decimal_places=4)
    fixed_years: int | None = Field(None, ge=1)
    review_frequency: REVIEW_FREQUENCIES | None = None

    # Closing costs options
    include_costs: bool = True
    property_type: PROPERTY_TYPES = "second_hand"
    region_tax_rate: Decimal | None = Field(None, ge=0, decimal_places=4)

    @model_validator(mode="after")
    def _validate_rate_params(self) -> MortgageSimulateRequest:
        if self.down_payment >= self.property_price:
            raise ValueError("down_payment must be less than property_price")

        if self.rate_type == "fixed":
            if self.interest_rate is None:
                raise ValueError("interest_rate is required for fixed mortgages")

        elif self.rate_type == "variable":
            if self.euribor_rate is None:
                raise ValueError("euribor_rate is required for variable mortgages")
            if self.spread is None:
                raise ValueError("spread is required for variable mortgages")

        else:  # mixed
            if self.interest_rate is None:
                raise ValueError("interest_rate is required for the fixed period of mixed mortgages")
            if self.euribor_rate is None:
                raise ValueError("euribor_rate is required for mixed mortgages")
            if self.spread is None:
                raise ValueError("spread is required for mixed mortgages")
            if self.fixed_years is None:
                raise ValueError("fixed_years is required for mixed mortgages")
            if self.fixed_years >= self.term_years:
                raise ValueError("fixed_years must be less than term_years")

        return self


class MortgageSimulationResult(BaseModel):
    loan_amount: Decimal
    rate_type: str
    term_years: int
    initial_monthly_payment: Decimal
    total_amount_paid: Decimal
    total_interest: Decimal
    effective_annual_rate: Decimal
    schedule: list[AmortizationRowSchema]
    closing_costs: ClosingCostsSchema | None


# ── Compare ───────────────────────────────────────────────────────────────────


class ScenarioParams(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate_type: RATE_TYPES
    interest_rate: Decimal | None = Field(None, ge=0, decimal_places=4)
    euribor_rate: Decimal | None = Field(None, decimal_places=4)
    spread: Decimal | None = Field(None, ge=0, decimal_places=4)
    fixed_years: int | None = Field(None, ge=1)
    review_frequency: REVIEW_FREQUENCIES | None = None

    @model_validator(mode="after")
    def _validate_scenario(self) -> ScenarioParams:
        if self.rate_type == "fixed" and self.interest_rate is None:
            raise ValueError("interest_rate is required for fixed scenarios")
        if self.rate_type == "variable":
            if self.euribor_rate is None or self.spread is None:
                raise ValueError("euribor_rate and spread are required for variable scenarios")
        if self.rate_type == "mixed":
            if self.interest_rate is None or self.euribor_rate is None or self.spread is None:
                raise ValueError(
                    "interest_rate, euribor_rate and spread are required for mixed scenarios"
                )
            if self.fixed_years is None:
                raise ValueError("fixed_years is required for mixed scenarios")
        return self


class MortgageCompareRequest(BaseModel):
    property_price: Decimal = Field(..., gt=0, decimal_places=2)
    down_payment: Decimal = Field(..., gt=0, decimal_places=2)
    term_years: int = Field(..., ge=5, le=40)
    scenarios: list[ScenarioParams] = Field(..., min_length=2, max_length=5)

    @model_validator(mode="after")
    def _validate_down_payment(self) -> MortgageCompareRequest:
        if self.down_payment >= self.property_price:
            raise ValueError("down_payment must be less than property_price")
        return self


class MortgageScenarioSummary(BaseModel):
    name: str
    rate_type: str
    initial_monthly_payment: Decimal
    total_amount_paid: Decimal
    total_interest: Decimal
    savings_vs_first: Decimal | None  # positive = cheaper than first scenario


class MortgageCompareResponse(BaseModel):
    loan_amount: Decimal
    term_years: int
    scenarios: list[MortgageScenarioSummary]


# ── Affordability ─────────────────────────────────────────────────────────────


class MaxLoanOption(BaseModel):
    description: str
    rate_type: str
    interest_rate: Decimal
    term_years: int
    max_loan: Decimal
    monthly_payment: Decimal


class AffordabilityResponse(BaseModel):
    monthly_net_income: Decimal
    max_monthly_payment: Decimal   # 35 % of income
    recommended_max_loan: Decimal  # at the most common scenario (fixed 25y)
    options: list[MaxLoanOption]


# ── Save / CRUD simulations ───────────────────────────────────────────────────


class MortgageSaveRequest(MortgageSimulateRequest):
    name: str = Field(..., min_length=1, max_length=150)


class MortgageSimulationResponse(BaseModel):
    id: uuid.UUID
    name: str
    property_price: Decimal
    down_payment: Decimal
    loan_amount: Decimal
    rate_type: str
    term_years: int
    interest_rate: Decimal | None
    euribor_rate: Decimal | None
    spread: Decimal | None
    fixed_years: int | None
    review_frequency: str | None
    property_type: str
    region_tax_rate: Decimal | None
    initial_monthly_payment: Decimal
    total_amount_paid: Decimal
    total_interest: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Affordability (Fase 4.3) ───────────────────────────────────────────────


class StressTestResult(BaseModel):
    euribor_rate: Decimal
    euribor_label: str
    max_loan_p10: Decimal
    max_loan_p50: Decimal
    max_loan_p90: Decimal
    monthly_payment_p50: Decimal
    is_affordable: bool


class AIAffordabilityResponse(BaseModel):
    # Capacidad basada en ingresos predichos por ML
    forecast_monthly_income_p10: Decimal
    forecast_monthly_income_p50: Decimal
    forecast_monthly_income_p90: Decimal
    forecast_max_monthly_payment: Decimal   # 35 % del income_p50 predicho
    forecast_recommended_max_loan: Decimal  # fijo 25 años al tipo de referencia

    # Comparación con capacidad actual (últimos 3 meses, método tradicional)
    current_based: AffordabilityResponse

    # Stress tests por nivel de Euríbor
    stress_tests: list[StressTestResult]

    # Metadatos
    ml_available: bool
    historical_months_used: int
    months_ahead_used: int
    model_used: str
