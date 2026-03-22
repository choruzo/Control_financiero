from typing import Literal

from pydantic import BaseModel, Field


class MonthlyPoint(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    income: float = Field(..., ge=0.0)
    expenses: float = Field(..., ge=0.0)


class ForecastPoint(BaseModel):
    year: int
    month: int
    income_p10: float
    income_p50: float
    income_p90: float
    expenses_p10: float
    expenses_p50: float
    expenses_p90: float
    net_p10: float
    net_p50: float
    net_p90: float


class ForecastRequest(BaseModel):
    historical_data: list[MonthlyPoint] = Field(..., min_length=1)
    months_ahead: int = Field(default=6, ge=1, le=12)
    include_intervals: bool = True


class ForecastResponse(BaseModel):
    predictions: list[ForecastPoint]
    model_used: Literal["lstm", "prophet", "degraded"]
    model_version: str
    data_months_provided: int


class ForecastRetrainResponse(BaseModel):
    status: str
    data_series_count: int
    reason: str | None = None
    model_version: str | None = None


class ForecastStatusResponse(BaseModel):
    loaded: bool
    model_version: str | None
    mae: float | None
    retrain_in_progress: bool
    min_months_required: int
    last_trained: str | None = None
