from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mortgage import MortgageSimulation
from app.models.transaction import Transaction
from app.schemas.mortgage import (
    AffordabilityResponse,
    MaxLoanOption,
    MortgageCompareRequest,
    MortgageCompareResponse,
    MortgageScenarioSummary,
    MortgageSaveRequest,
    MortgageSimulateRequest,
    MortgageSimulationResult,
    ScenarioParams,
)
from app.utils.mortgage import (
    AmortizationRow,
    ClosingCostsResult,
    amortization_schedule,
    closing_costs,
    effective_annual_rate,
    monthly_payment,
)

_TWO = Decimal("0.01")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _q2(value: Decimal) -> Decimal:
    return value.quantize(_TWO, rounding=ROUND_HALF_UP)


def _review_months(review_frequency: str | None) -> int:
    return 6 if review_frequency == "semiannual" else 12


def _build_result(
    loan_amount: Decimal,
    rate_type: str,
    term_years: int,
    schedule: list[AmortizationRow],
    costs: ClosingCostsResult | None,
) -> MortgageSimulationResult:
    from app.schemas.mortgage import AmortizationRowSchema, ClosingCostsSchema

    first_payment = schedule[0].payment if schedule else Decimal("0.00")
    total_paid = _q2(sum(row.payment for row in schedule))
    total_interest = _q2(total_paid - loan_amount)

    ear = effective_annual_rate(first_payment, loan_amount, term_years)

    schedule_schemas = [
        AmortizationRowSchema(
            month=row.month,
            payment=row.payment,
            principal=row.principal,
            interest=row.interest,
            balance=row.balance,
            applied_rate=row.applied_rate,
        )
        for row in schedule
    ]

    costs_schema: ClosingCostsSchema | None = None
    if costs is not None:
        costs_schema = ClosingCostsSchema(
            notary=costs.notary,
            registry=costs.registry,
            tax=costs.tax,
            gestor=costs.gestor,
            appraisal=costs.appraisal,
            total=costs.total,
        )

    return MortgageSimulationResult(
        loan_amount=loan_amount,
        rate_type=rate_type,
        term_years=term_years,
        initial_monthly_payment=first_payment,
        total_amount_paid=total_paid,
        total_interest=total_interest,
        effective_annual_rate=ear,
        schedule=schedule_schemas,
        closing_costs=costs_schema,
    )


def _simulate_from_request(data: MortgageSimulateRequest) -> MortgageSimulationResult:
    loan_amount = _q2(data.property_price - data.down_payment)
    review_months = _review_months(data.review_frequency)

    schedule = amortization_schedule(
        principal=loan_amount,
        annual_rate_pct=data.interest_rate or Decimal("0"),
        term_years=data.term_years,
        rate_type=data.rate_type,
        euribor_rate=data.euribor_rate,
        spread=data.spread,
        fixed_years=data.fixed_years,
        review_months=review_months,
    )

    costs: ClosingCostsResult | None = None
    if data.include_costs:
        costs = closing_costs(
            property_price=data.property_price,
            property_type=data.property_type,
            region_tax_rate=data.region_tax_rate,
        )

    return _build_result(loan_amount, data.rate_type, data.term_years, schedule, costs)


def _simulate_scenario(
    loan_amount: Decimal,
    term_years: int,
    scenario: ScenarioParams,
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (initial_monthly_payment, total_paid, total_interest) for a scenario."""
    review_months = _review_months(scenario.review_frequency)
    schedule = amortization_schedule(
        principal=loan_amount,
        annual_rate_pct=scenario.interest_rate or Decimal("0"),
        term_years=term_years,
        rate_type=scenario.rate_type,
        euribor_rate=scenario.euribor_rate,
        spread=scenario.spread,
        fixed_years=scenario.fixed_years,
        review_months=review_months,
    )
    first = schedule[0].payment if schedule else Decimal("0.00")
    total = _q2(sum(row.payment for row in schedule))
    interest = _q2(total - loan_amount)
    return first, total, interest


def _max_loan_for_payment(
    max_monthly: Decimal, annual_rate_pct: Decimal, term_years: int
) -> Decimal:
    """Invert the PMT formula: given a max payment, find the maximum loan amount."""
    r = annual_rate_pct / Decimal("100") / Decimal("12")
    n = term_years * 12
    if r == 0:
        return _q2(max_monthly * Decimal(str(n)))
    factor = (1 + r) ** n  # type: ignore[operator]
    loan = max_monthly * (factor - 1) / (r * factor)
    return _q2(loan)


async def _get_simulation_or_404(
    db: AsyncSession, user_id: uuid.UUID, sim_id: uuid.UUID
) -> MortgageSimulation:
    result = await db.execute(
        select(MortgageSimulation).where(
            MortgageSimulation.id == sim_id,
            MortgageSimulation.user_id == user_id,
        )
    )
    sim = result.scalar_one_or_none()
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    return sim


# ── Public API ────────────────────────────────────────────────────────────────


async def simulate_mortgage(data: MortgageSimulateRequest) -> MortgageSimulationResult:
    """Stateless calculation — does not persist anything."""
    return _simulate_from_request(data)


async def compare_scenarios(data: MortgageCompareRequest) -> MortgageCompareResponse:
    """Compare multiple mortgage scenarios for the same property and term."""
    loan_amount = _q2(data.property_price - data.down_payment)

    summaries: list[MortgageScenarioSummary] = []
    first_total: Decimal | None = None

    for scenario in data.scenarios:
        first_pmt, total_paid, total_interest = _simulate_scenario(
            loan_amount, data.term_years, scenario
        )
        if first_total is None:
            first_total = total_paid

        savings = _q2(first_total - total_paid) if first_total != total_paid else None

        summaries.append(
            MortgageScenarioSummary(
                name=scenario.name,
                rate_type=scenario.rate_type,
                initial_monthly_payment=first_pmt,
                total_amount_paid=total_paid,
                total_interest=total_interest,
                savings_vs_first=savings,
            )
        )

    return MortgageCompareResponse(
        loan_amount=loan_amount,
        term_years=data.term_years,
        scenarios=summaries,
    )


async def get_affordability(
    db: AsyncSession, user_id: uuid.UUID
) -> AffordabilityResponse:
    """Calculate how much mortgage the user can afford based on their income.

    Uses the last 3 months of income transactions to estimate monthly net income,
    then applies the 35 % debt-to-income rule.
    """
    from calendar import monthrange
    from datetime import UTC, date, datetime

    today = datetime.now(UTC).date()

    # Build a 3-month window ending this month
    months: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(3):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    total_income = Decimal("0.00")
    for year, month in months:
        _, last_day = monthrange(year, month)
        result = await db.execute(
            select(func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0"))).where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "income",
                Transaction.date >= date(year, month, 1),
                Transaction.date <= date(year, month, last_day),
            )
        )
        total_income += Decimal(str(result.scalar_one()))

    monthly_income = _q2(total_income / Decimal("3"))
    max_monthly = _q2(monthly_income * Decimal("0.35"))

    # Generate affordability options for common scenarios
    option_configs = [
        ("Fijo 15 años al 3.5 %", "fixed", Decimal("3.5"), 15),
        ("Fijo 20 años al 3.5 %", "fixed", Decimal("3.5"), 20),
        ("Fijo 25 años al 3.5 %", "fixed", Decimal("3.5"), 25),
        ("Fijo 30 años al 3.5 %", "fixed", Decimal("3.5"), 30),
        ("Variable 20 años (Eur 3.5 % + 0.8 %)", "variable", Decimal("4.3"), 20),
        ("Variable 30 años (Eur 3.5 % + 0.8 %)", "variable", Decimal("4.3"), 30),
    ]

    options: list[MaxLoanOption] = []
    for description, rate_type, rate, years in option_configs:
        max_loan = _max_loan_for_payment(max_monthly, rate, years)
        pmt = monthly_payment(max_loan, rate, years)
        options.append(
            MaxLoanOption(
                description=description,
                rate_type=rate_type,
                interest_rate=rate,
                term_years=years,
                max_loan=max_loan,
                monthly_payment=pmt,
            )
        )

    # Recommended = fixed 25 years (index 2)
    recommended_max_loan = options[2].max_loan if len(options) > 2 else Decimal("0.00")

    return AffordabilityResponse(
        monthly_net_income=monthly_income,
        max_monthly_payment=max_monthly,
        recommended_max_loan=recommended_max_loan,
        options=options,
    )


# ── CRUD simulations ──────────────────────────────────────────────────────────


async def save_simulation(
    db: AsyncSession, user_id: uuid.UUID, data: MortgageSaveRequest
) -> MortgageSimulation:
    """Calculate and persist a named mortgage simulation."""
    result = _simulate_from_request(data)
    loan_amount = _q2(data.property_price - data.down_payment)

    sim = MortgageSimulation(
        user_id=user_id,
        name=data.name,
        property_price=data.property_price,
        down_payment=data.down_payment,
        loan_amount=loan_amount,
        rate_type=data.rate_type,
        term_years=data.term_years,
        interest_rate=data.interest_rate,
        euribor_rate=data.euribor_rate,
        spread=data.spread,
        fixed_years=data.fixed_years,
        review_frequency=data.review_frequency,
        property_type=data.property_type,
        region_tax_rate=data.region_tax_rate,
        initial_monthly_payment=result.initial_monthly_payment,
        total_amount_paid=result.total_amount_paid,
        total_interest=result.total_interest,
    )
    db.add(sim)
    await db.flush()
    return sim


async def list_simulations(
    db: AsyncSession, user_id: uuid.UUID
) -> list[MortgageSimulation]:
    result = await db.execute(
        select(MortgageSimulation)
        .where(MortgageSimulation.user_id == user_id)
        .order_by(MortgageSimulation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_simulation(
    db: AsyncSession, user_id: uuid.UUID, sim_id: uuid.UUID
) -> MortgageSimulation:
    return await _get_simulation_or_404(db, user_id, sim_id)


async def delete_simulation(
    db: AsyncSession, user_id: uuid.UUID, sim_id: uuid.UUID
) -> None:
    sim = await _get_simulation_or_404(db, user_id, sim_id)
    await db.delete(sim)
    await db.flush()
