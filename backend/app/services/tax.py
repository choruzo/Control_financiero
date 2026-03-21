from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax import TaxBracket, TaxConfig
from app.schemas.tax import (
    BracketBreakdown,
    TaxCalculationResponse,
    TaxConfigCreate,
    TaxConfigUpdate,
)

_TWO = Decimal("0.01")
_FOUR = Decimal("0.0001")

# ── Social Security constants ─────────────────────────────────────────────────
# Source: BOE Orden PJC/178/2025 (2025) and Orden cotización 2026
_SS_PARAMS: dict[int, dict[str, Decimal]] = {
    2025: {
        "rate": Decimal("0.0635"),
        "max_base_monthly": Decimal("4909.50"),
    },
    2026: {
        "rate": Decimal("0.0650"),
        "max_base_monthly": Decimal("5101.20"),
    },
}
_SS_DEFAULT_RATE = Decimal("0.0635")
_SS_DEFAULT_MAX = Decimal("4909.50")

# Standard deductions (simplified)
_WORK_EXPENSES_DEDUCTION = Decimal("2000.00")
_PERSONAL_ALLOWANCE = Decimal("5550.00")  # mínimo personal básico

# ── Seed data ─────────────────────────────────────────────────────────────────
# Combined IRPF scale (estatal + autonómica media) — same for 2025 and 2026
# Source: AEAT / Agencia Tributaria España
_GENERAL_BRACKETS = [
    (Decimal("0"), Decimal("12450.00"), Decimal("0.1900")),
    (Decimal("12450.00"), Decimal("20200.00"), Decimal("0.2400")),
    (Decimal("20200.00"), Decimal("35200.00"), Decimal("0.3000")),
    (Decimal("35200.00"), Decimal("60000.00"), Decimal("0.3700")),
    (Decimal("60000.00"), Decimal("300000.00"), Decimal("0.4500")),
    (Decimal("300000.00"), None, Decimal("0.4700")),
]

_SAVINGS_BRACKETS = [
    (Decimal("0"), Decimal("6000.00"), Decimal("0.1900")),
    (Decimal("6000.00"), Decimal("50000.00"), Decimal("0.2100")),
    (Decimal("50000.00"), Decimal("200000.00"), Decimal("0.2300")),
    (Decimal("200000.00"), Decimal("300000.00"), Decimal("0.2700")),
    (Decimal("300000.00"), None, Decimal("0.3000")),
]

_SEED_YEARS = [2025, 2026]


# ── Pure helpers ──────────────────────────────────────────────────────────────


def _q2(v: Decimal) -> Decimal:
    return v.quantize(_TWO, rounding=ROUND_HALF_UP)


def _q4(v: Decimal) -> Decimal:
    return v.quantize(_FOUR, rounding=ROUND_HALF_UP)


def _apply_brackets(
    amount: Decimal,
    brackets: list[TaxBracket],
) -> tuple[Decimal, list[BracketBreakdown]]:
    """Apply progressive IRPF brackets to *amount*.

    Returns (total_tax, breakdown_per_bracket).
    """
    total = Decimal("0")
    breakdown: list[BracketBreakdown] = []
    remaining = amount

    for bracket in sorted(brackets, key=lambda b: b.min_amount):
        if remaining <= 0:
            break
        bracket_size = (
            bracket.max_amount - bracket.min_amount
            if bracket.max_amount is not None
            else remaining
        )
        taxable_here = min(remaining, bracket_size)
        tax_here = _q2(taxable_here * bracket.rate)
        total += tax_here
        breakdown.append(
            BracketBreakdown(
                rate=bracket.rate,
                taxable_in_bracket=_q2(taxable_here),
                tax_in_bracket=tax_here,
            )
        )
        remaining -= taxable_here

    return _q2(total), breakdown


# ── Seeder ────────────────────────────────────────────────────────────────────


async def seed_tax_brackets(db: AsyncSession) -> None:
    """Idempotently insert IRPF brackets for all seed years."""
    for year in _SEED_YEARS:
        existing = await db.execute(
            select(TaxBracket).where(TaxBracket.tax_year == year).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue  # already seeded for this year

        for min_amt, max_amt, rate in _GENERAL_BRACKETS:
            db.add(
                TaxBracket(
                    tax_year=year,
                    bracket_type="general",
                    min_amount=min_amt,
                    max_amount=max_amt,
                    rate=rate,
                )
            )
        for min_amt, max_amt, rate in _SAVINGS_BRACKETS:
            db.add(
                TaxBracket(
                    tax_year=year,
                    bracket_type="savings",
                    min_amount=min_amt,
                    max_amount=max_amt,
                    rate=rate,
                )
            )


# ── Brackets query ────────────────────────────────────────────────────────────


async def list_brackets(
    db: AsyncSession,
    year: int | None = None,
    bracket_type: str | None = None,
) -> list[TaxBracket]:
    q = select(TaxBracket)
    if year is not None:
        q = q.where(TaxBracket.tax_year == year)
    if bracket_type is not None:
        q = q.where(TaxBracket.bracket_type == bracket_type)
    q = q.order_by(TaxBracket.tax_year, TaxBracket.bracket_type, TaxBracket.min_amount)
    result = await db.execute(q)
    return list(result.scalars().all())


# ── TaxConfig CRUD ────────────────────────────────────────────────────────────


async def _get_config_or_404(
    db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID
) -> TaxConfig:
    result = await db.execute(
        select(TaxConfig).where(TaxConfig.id == config_id, TaxConfig.user_id == user_id)
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax config not found")
    return cfg


async def create_tax_config(
    db: AsyncSession, user_id: uuid.UUID, data: TaxConfigCreate
) -> TaxConfig:
    existing = await db.execute(
        select(TaxConfig).where(
            TaxConfig.user_id == user_id, TaxConfig.tax_year == data.tax_year
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tax config for year {data.tax_year} already exists",
        )
    cfg = TaxConfig(
        user_id=user_id,
        tax_year=data.tax_year,
        gross_annual_salary=data.gross_annual_salary,
    )
    db.add(cfg)
    await db.flush()
    return cfg


async def list_tax_configs(db: AsyncSession, user_id: uuid.UUID) -> list[TaxConfig]:
    result = await db.execute(
        select(TaxConfig)
        .where(TaxConfig.user_id == user_id)
        .order_by(TaxConfig.tax_year.desc())
    )
    return list(result.scalars().all())


async def get_tax_config(
    db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID
) -> TaxConfig:
    return await _get_config_or_404(db, user_id, config_id)


async def update_tax_config(
    db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID, data: TaxConfigUpdate
) -> TaxConfig:
    cfg = await _get_config_or_404(db, user_id, config_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cfg, field, value)
    await db.flush()
    return cfg


async def delete_tax_config(
    db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID
) -> None:
    cfg = await _get_config_or_404(db, user_id, config_id)
    await db.delete(cfg)
    await db.flush()


# ── IRPF calculation ──────────────────────────────────────────────────────────


async def calculate_tax(
    db: AsyncSession, user_id: uuid.UUID, config_id: uuid.UUID
) -> TaxCalculationResponse:
    cfg = await _get_config_or_404(db, user_id, config_id)
    year = cfg.tax_year
    gross = cfg.gross_annual_salary

    # 1. Social Security
    ss_params = _SS_PARAMS.get(
        year, {"rate": _SS_DEFAULT_RATE, "max_base_monthly": _SS_DEFAULT_MAX}
    )
    ss_rate = ss_params["rate"]
    max_base_monthly = ss_params["max_base_monthly"]
    gross_monthly = _q2(gross / Decimal("12"))
    ss_monthly_base = min(gross_monthly, max_base_monthly)
    ss_annual = _q2(ss_monthly_base * Decimal("12") * ss_rate)

    # 2. Work expenses deduction (flat)
    work_exp = _WORK_EXPENSES_DEDUCTION

    # 3. Taxable base (rendimiento neto del trabajo before mínimo personal)
    taxable_base = max(Decimal("0"), _q2(gross - ss_annual - work_exp))

    # 4. Load brackets for the year
    bracket_result = await db.execute(
        select(TaxBracket).where(
            TaxBracket.tax_year == year, TaxBracket.bracket_type == "general"
        )
    )
    brackets = list(bracket_result.scalars().all())

    # 5. Compute IRPF on taxable base
    cuota_integra, breakdown = _apply_brackets(taxable_base, brackets)

    # 6. Mínimo personal deduction (reduces quota, not base)
    personal_allowance_deduction, _ = _apply_brackets(_PERSONAL_ALLOWANCE, brackets)
    irpf_annual = max(Decimal("0"), _q2(cuota_integra - personal_allowance_deduction))

    # 7. Effective rate over gross (to 4 decimal places)
    effective_rate = _q4(irpf_annual / gross * Decimal("100")) if gross > 0 else Decimal("0")

    # 8. Net
    net_annual = _q2(gross - ss_annual - irpf_annual)
    net_monthly = _q2(net_annual / Decimal("12"))

    return TaxCalculationResponse(
        tax_year=year,
        gross_annual=gross,
        ss_annual=ss_annual,
        ss_rate=ss_rate,
        work_expenses_deduction=work_exp,
        taxable_base=taxable_base,
        irpf_annual=irpf_annual,
        effective_rate=effective_rate,
        net_annual=net_annual,
        net_monthly=net_monthly,
        bracket_breakdown=breakdown,
    )
