"""
Servicio del motor de escenarios "what-if" (Fase 4.2).

Orquesta:
  1. Datos históricos (analytics)
  2. Forecast ML (ml_client)
  3. Impacto Euríbor (MortgageSimulation)
  4. Impacto fiscal (IRPF puro sin TaxConfig en BD)
  5. Monte Carlo por mes
  6. Construcción del resumen
"""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mortgage import MortgageSimulation
from app.schemas.scenarios import (
    ScenarioMonthResult,
    ScenarioRequest,
    ScenarioResponse,
    ScenarioSummary,
)
from app.services import analytics as analytics_svc
from app.services.ml_client import MLClient
from app.utils import monte_carlo
from app.utils.mortgage import monthly_payment

logger = structlog.get_logger(__name__)

_TWO = Decimal("0.01")
_FOUR = Decimal("0.0001")

# ── IRPF constants (replicados de services/tax.py sin importar BD) ────────────

_SS_PARAMS: dict[int, dict[str, Decimal]] = {
    2025: {"rate": Decimal("0.0635"), "max_base_monthly": Decimal("4909.50")},
    2026: {"rate": Decimal("0.0650"), "max_base_monthly": Decimal("5101.20")},
}
_SS_DEFAULT_RATE = Decimal("0.0635")
_SS_DEFAULT_MAX = Decimal("4909.50")
_WORK_EXPENSES_DEDUCTION = Decimal("2000.00")
_PERSONAL_ALLOWANCE = Decimal("5550.00")

# Tramos IRPF general (escala estatal + autonómica media) — mismo 2025/2026
_GENERAL_BRACKETS = [
    (Decimal("0"), Decimal("12450.00"), Decimal("0.1900")),
    (Decimal("12450.00"), Decimal("20200.00"), Decimal("0.2400")),
    (Decimal("20200.00"), Decimal("35200.00"), Decimal("0.3000")),
    (Decimal("35200.00"), Decimal("60000.00"), Decimal("0.3700")),
    (Decimal("60000.00"), Decimal("300000.00"), Decimal("0.4500")),
    (Decimal("300000.00"), None, Decimal("0.4700")),
]

ml_client = MLClient()


def _q2(v: Decimal) -> Decimal:
    return v.quantize(_TWO, rounding=ROUND_HALF_UP)


def _apply_brackets_pure(amount: Decimal) -> Decimal:
    """Aplica los tramos IRPF generales sobre *amount* y devuelve el total."""
    total = Decimal("0")
    remaining = amount
    for min_amt, max_amt, rate in _GENERAL_BRACKETS:
        if remaining <= 0:
            break
        bracket_size = (max_amt - min_amt) if max_amt is not None else remaining
        taxable_here = min(remaining, bracket_size)
        total += _q2(taxable_here * rate)
        remaining -= taxable_here
    return _q2(total)


def _irpf_monthly(gross_annual: Decimal, year: int) -> Decimal:
    """Devuelve la cuota mensual IRPF + SS neta para un bruto anual dado.

    Replica la lógica de calculate_tax() sin necesitar BD ni TaxConfig.
    """
    ss_params = _SS_PARAMS.get(year, {"rate": _SS_DEFAULT_RATE, "max_base_monthly": _SS_DEFAULT_MAX})
    ss_rate = ss_params["rate"]
    max_base_monthly = ss_params["max_base_monthly"]

    gross_monthly = _q2(gross_annual / Decimal("12"))
    ss_monthly_base = min(gross_monthly, max_base_monthly)
    ss_annual = _q2(ss_monthly_base * Decimal("12") * ss_rate)

    taxable_base = max(Decimal("0"), _q2(gross_annual - ss_annual - _WORK_EXPENSES_DEDUCTION))

    cuota_integra = _apply_brackets_pure(taxable_base)
    personal_allowance_deduction = _apply_brackets_pure(_PERSONAL_ALLOWANCE)
    irpf_annual = max(Decimal("0"), _q2(cuota_integra - personal_allowance_deduction))

    # Retención mensual total (SS + IRPF)
    total_monthly = _q2((ss_annual + irpf_annual) / Decimal("12"))
    return total_monthly


async def _calc_euribor_impact(
    db: AsyncSession,
    user_id: uuid.UUID,
    euribor_variation_pct: Decimal | None,
) -> Decimal:
    """Calcula el delta mensual de cuota hipotecaria ante un cambio de Euríbor.

    Busca la simulación variable/mixta más reciente del usuario.
    Devuelve 0 si no existe simulación o la variación es None.
    """
    if euribor_variation_pct is None:
        return Decimal("0")

    result = await db.execute(
        select(MortgageSimulation)
        .where(
            MortgageSimulation.user_id == user_id,
            MortgageSimulation.rate_type.in_(["variable", "mixed"]),
        )
        .order_by(MortgageSimulation.created_at.desc())
        .limit(1)
    )
    sim = result.scalar_one_or_none()
    if sim is None:
        return Decimal("0")

    # Euríbor actual + delta
    current_euribor = sim.euribor_rate or Decimal("0")
    new_euribor = current_euribor + euribor_variation_pct
    spread = sim.spread or Decimal("0")

    new_rate = new_euribor + spread
    current_rate = current_euribor + spread

    # Cuota nueva vs actual (usamos term_years como aproximación del plazo restante)
    try:
        new_pmt = monthly_payment(sim.loan_amount, new_rate, sim.term_years)
        current_pmt = monthly_payment(sim.loan_amount, current_rate, sim.term_years)
        return _q2(new_pmt - current_pmt)
    except (ZeroDivisionError, Exception):
        return Decimal("0")


def _build_summary(
    monthly_results: list[ScenarioMonthResult],
    tax_base_monthly: Decimal | None,
    tax_scenario_monthly: Decimal | None,
) -> ScenarioSummary:
    """Agrega los resultados mensuales en un resumen del período."""
    period = len(monthly_results)
    total_base = sum((r.base_net for r in monthly_results), Decimal("0"))
    total_p50 = sum((r.scenario_net_p50 for r in monthly_results), Decimal("0"))
    total_p10 = sum((r.scenario_net_p10 for r in monthly_results), Decimal("0"))
    total_p90 = sum((r.scenario_net_p90 for r in monthly_results), Decimal("0"))

    improvement = _q2(total_p50 - total_base)
    improvement_p10 = _q2(total_p10 - total_base)
    improvement_p90 = _q2(total_p90 - total_base)

    avg_monthly = _q2(improvement / Decimal(period)) if period > 0 else Decimal("0")

    pct = None
    if total_base != 0:
        pct = _q2(improvement / abs(total_base) * Decimal("100"))

    tax_impact = None
    if tax_base_monthly is not None and tax_scenario_monthly is not None:
        tax_impact = _q2((tax_scenario_monthly - tax_base_monthly) * Decimal(period))

    return ScenarioSummary(
        period_months=period,
        total_base_net=_q2(total_base),
        total_scenario_net_p50=_q2(total_p50),
        total_net_improvement=improvement,
        total_net_improvement_p10=improvement_p10,
        total_net_improvement_p90=improvement_p90,
        avg_monthly_improvement=avg_monthly,
        net_improvement_pct=pct,
        total_tax_impact=tax_impact,
    )


async def analyze_scenario(
    db: AsyncSession,
    user_id: uuid.UUID,
    request: ScenarioRequest,
) -> ScenarioResponse:
    """Motor principal del análisis de escenarios.

    Pipeline:
    1. Datos históricos del usuario (últimos 24 meses)
    2. Delta de gastos recurrentes (determinista)
    3. Impacto Euríbor (busca MortgageSimulation variable/mixta)
    4. Forecast ML (1 llamada HTTP, degradación graceful)
    5. Impacto fiscal IRPF (puro, sin BD)
    6. Monte Carlo por mes
    7. Construcción del resumen
    """
    # 1. Datos históricos
    cashflow = await analytics_svc.get_cashflow(db, user_id, months=24)
    recent = [m for m in cashflow if m.total_income > 0 or m.total_expenses > 0]

    # 2. Delta gastos recurrentes
    expense_delta = Decimal("0")
    for mod in request.recurring_expense_modifications:
        if mod.action == "add":
            expense_delta += mod.monthly_amount
        else:
            expense_delta -= mod.monthly_amount

    # 3. Impacto Euríbor
    mortgage_delta = await _calc_euribor_impact(db, user_id, request.euribor_variation_pct)
    total_expense_delta = expense_delta + mortgage_delta

    # 4. Forecast ML
    historical_ml = [
        {
            "year": m.year,
            "month": m.month,
            "income": float(m.total_income),
            "expenses": float(m.total_expenses),
        }
        for m in recent
    ]

    forecast = await ml_client.forecast(historical_ml, request.months_ahead)
    ml_available = forecast.ml_available

    # Fallback: si no hay predicciones (ML y datos insuficientes)
    if not forecast.predictions:
        # Usar promedio histórico como base
        if recent:
            avg_income = sum(float(m.total_income) for m in recent) / len(recent)
            avg_expenses = sum(float(m.total_expenses) for m in recent) / len(recent)
        else:
            avg_income = 0.0
            avg_expenses = 0.0
        sigma_pct = 0.10
        from app.services.ml_client import MLClient as _MLClient
        fallback = _MLClient._unavailable_forecast_response(historical_ml, request.months_ahead)
        # Override con el promedio histórico
        for pt in fallback.predictions:
            pt.income_p50 = avg_income
            pt.income_p10 = max(0.0, avg_income * (1 - sigma_pct * 1.28))
            pt.income_p90 = avg_income * (1 + sigma_pct * 1.28)
            pt.expenses_p50 = avg_expenses
            pt.expenses_p10 = max(0.0, avg_expenses * (1 - sigma_pct * 1.28))
            pt.expenses_p90 = avg_expenses * (1 + sigma_pct * 1.28)
            pt.net_p50 = avg_income - avg_expenses
            pt.net_p10 = pt.income_p10 - pt.expenses_p90
            pt.net_p90 = pt.income_p90 - pt.expenses_p10
        forecast = fallback

    # 5. Impacto fiscal (puro, sin BD)
    tax_base_monthly: Decimal | None = None
    tax_scenario_monthly: Decimal | None = None
    if request.gross_annual is not None:
        tax_base_monthly = _irpf_monthly(request.gross_annual, request.tax_year)
        income_mult = Decimal("1") + request.salary_variation_pct / Decimal("100")
        modified_gross = _q2(request.gross_annual * income_mult)
        tax_scenario_monthly = _irpf_monthly(modified_gross, request.tax_year)

    # 6. Monte Carlo por mes
    income_mult_f = float(Decimal("1") + request.salary_variation_pct / Decimal("100"))
    expense_delta_f = float(total_expense_delta)
    n_sim = request.monte_carlo_simulations

    monthly_results: list[ScenarioMonthResult] = []
    for pred in forecast.predictions:
        base_income = Decimal(str(round(pred.income_p50, 2)))
        base_expenses = Decimal(str(round(pred.expenses_p50, 2)))
        base_net = _q2(base_income - base_expenses)

        scenario_income = _q2(base_income * Decimal(str(income_mult_f)))
        scenario_expenses = _q2(base_expenses + total_expense_delta)

        net_p10, net_p50, net_p90 = monte_carlo.simulate_net_distribution(
            income_p50=float(scenario_income),
            income_p10=max(0.0, pred.income_p10 * income_mult_f),
            income_p90=pred.income_p90 * income_mult_f,
            expenses_p50=float(scenario_expenses),
            expenses_p10=max(0.0, pred.expenses_p10 + expense_delta_f),
            expenses_p90=pred.expenses_p90 + expense_delta_f,
            n=n_sim,
        )

        tax_delta = None
        if tax_base_monthly is not None and tax_scenario_monthly is not None:
            tax_delta = _q2(tax_scenario_monthly - tax_base_monthly)

        monthly_results.append(
            ScenarioMonthResult(
                year=pred.year,
                month=pred.month,
                base_income=base_income,
                base_expenses=base_expenses,
                base_net=base_net,
                scenario_income=scenario_income,
                scenario_expenses=_q2(scenario_expenses),
                scenario_net_p10=_q2(Decimal(str(net_p10))),
                scenario_net_p50=_q2(Decimal(str(net_p50))),
                scenario_net_p90=_q2(Decimal(str(net_p90))),
                tax_monthly_base=tax_base_monthly,
                tax_monthly_scenario=tax_scenario_monthly,
                tax_monthly_delta=tax_delta,
            )
        )

    # 7. Resumen
    summary = _build_summary(monthly_results, tax_base_monthly, tax_scenario_monthly)

    return ScenarioResponse(
        name=request.name,
        parameters=request,
        historical_months_used=len(recent),
        ml_available=ml_available,
        mortgage_impact_per_month=mortgage_delta if request.euribor_variation_pct is not None else None,
        monthly_results=monthly_results,
        summary=summary,
    )
