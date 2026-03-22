from decimal import Decimal

from pydantic import BaseModel


class ForecastMonthResponse(BaseModel):
    year: int
    month: int
    income_p10: Decimal
    income_p50: Decimal
    income_p90: Decimal
    expenses_p10: Decimal
    expenses_p50: Decimal
    expenses_p90: Decimal
    net_p10: Decimal
    net_p50: Decimal
    net_p90: Decimal


class CashflowForecastResponse(BaseModel):
    predictions: list[ForecastMonthResponse]
    model_used: str
    model_version: str
    historical_months_used: int
    ml_available: bool
