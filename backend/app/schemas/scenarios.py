"""Schemas Pydantic para el motor de escenarios "what-if" (Fase 4.2)."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class RecurringExpenseModification(BaseModel):
    """Modificación de un gasto recurrente mensual."""

    description: str = Field(..., max_length=200)
    monthly_amount: Decimal = Field(..., ge=Decimal("0.01"))
    action: Literal["add", "remove"]


class ScenarioRequest(BaseModel):
    """Parámetros de entrada del motor de escenarios."""

    name: str = Field(default="Escenario", max_length=100)
    months_ahead: int = Field(default=6, ge=1, le=24)

    # Variación de ingresos
    salary_variation_pct: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("-100"),
        le=Decimal("500"),
        description="Variación del sueldo en % (ej. 10 = +10%)",
    )

    # Impacto Euríbor (opcional)
    euribor_variation_pct: Decimal | None = Field(
        default=None,
        ge=Decimal("-5"),
        le=Decimal("15"),
        description="Variación del Euríbor en puntos porcentuales (ej. 1.5 = +1.5pp)",
    )

    # Modificaciones de gastos recurrentes
    recurring_expense_modifications: list[RecurringExpenseModification] = Field(
        default_factory=list
    )

    # Impacto fiscal (opcional)
    gross_annual: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description="Salario bruto anual para calcular impacto fiscal",
    )
    tax_year: int = Field(default=2026, ge=2025, le=2027)

    # Monte Carlo
    monte_carlo_simulations: int = Field(default=1000, ge=100, le=5000)


class ScenarioMonthResult(BaseModel):
    """Resultado del escenario para un mes concreto."""

    year: int
    month: int

    # Baseline del forecast (sin modificaciones)
    base_income: Decimal
    base_expenses: Decimal
    base_net: Decimal

    # Escenario con modificaciones aplicadas
    scenario_income: Decimal
    scenario_expenses: Decimal

    # Distribución Monte Carlo del neto del escenario
    scenario_net_p10: Decimal
    scenario_net_p50: Decimal
    scenario_net_p90: Decimal

    # Impacto fiscal (None si no se proporcionó gross_annual)
    tax_monthly_base: Decimal | None = None
    tax_monthly_scenario: Decimal | None = None
    tax_monthly_delta: Decimal | None = None


class ScenarioSummary(BaseModel):
    """Resumen agregado de todo el período analizado."""

    period_months: int

    # Neto total base vs escenario
    total_base_net: Decimal
    total_scenario_net_p50: Decimal
    total_net_improvement: Decimal  # p50 - base

    # Rangos de incertidumbre de la mejora
    total_net_improvement_p10: Decimal
    total_net_improvement_p90: Decimal

    avg_monthly_improvement: Decimal
    net_improvement_pct: Decimal | None  # None si base_net == 0

    # Impacto fiscal total (None si no aplica)
    total_tax_impact: Decimal | None = None


class ScenarioResponse(BaseModel):
    """Respuesta completa del análisis de escenario."""

    name: str
    parameters: ScenarioRequest
    historical_months_used: int
    ml_available: bool

    # Delta mensual de hipoteca por variación Euríbor (None si no aplica)
    mortgage_impact_per_month: Decimal | None = None

    monthly_results: list[ScenarioMonthResult]
    summary: ScenarioSummary
