"""Pure mortgage calculation utilities (no DB, no async).

Implements the French amortization system (cuota constante / sistema francés)
for fixed, variable and mixed rate mortgages.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class AmortizationRow:
    month: int
    payment: Decimal
    principal: Decimal
    interest: Decimal
    balance: Decimal
    applied_rate: Decimal  # annual rate applied this month (useful for variable)


@dataclass
class ClosingCostsResult:
    notary: Decimal
    registry: Decimal
    tax: Decimal       # ITP (second hand) or AJD (new)
    gestor: Decimal
    appraisal: Decimal
    total: Decimal


# ── Constants ─────────────────────────────────────────────────────────────────

_TWO = Decimal("0.01")
_FOUR = Decimal("0.0001")

# Default closing cost rates
_NOTARY_RATE = Decimal("0.005")       # 0.5 % of property price
_REGISTRY_RATE = Decimal("0.0015")    # 0.15 % of property price
_GESTOR_FIXED = Decimal("350.00")
_APPRAISAL_FIXED = Decimal("450.00")
_ITP_DEFAULT = Decimal("0.08")        # 8 % — second hand
_AJD_DEFAULT = Decimal("0.01")        # 1.0 % — new build


# ── Helpers ───────────────────────────────────────────────────────────────────


def _q2(value: Decimal) -> Decimal:
    return value.quantize(_TWO, rounding=ROUND_HALF_UP)


def _monthly_rate(annual_rate_pct: Decimal) -> Decimal:
    """Convert annual percentage rate to monthly decimal rate."""
    return annual_rate_pct / Decimal("100") / Decimal("12")


def _pmt(principal: Decimal, monthly_rate: Decimal, n_months: int) -> Decimal:
    """French amortization constant monthly payment (PMT formula).

    PMT = P × r(1+r)^n / [(1+r)^n − 1]

    When rate == 0 the payment is simply principal / n_months.
    """
    if monthly_rate == 0:
        return _q2(principal / Decimal(str(n_months)))
    factor = (1 + monthly_rate) ** n_months  # type: ignore[operator]
    pmt = principal * monthly_rate * factor / (factor - 1)
    return _q2(pmt)


# ── Public API ────────────────────────────────────────────────────────────────


def monthly_payment(
    principal: Decimal,
    annual_rate_pct: Decimal,
    term_years: int,
) -> Decimal:
    """Return the constant monthly payment for a fixed-rate mortgage."""
    r = _monthly_rate(annual_rate_pct)
    n = term_years * 12
    return _pmt(principal, r, n)


def amortization_schedule(
    principal: Decimal,
    annual_rate_pct: Decimal,
    term_years: int,
    rate_type: str,
    euribor_rate: Decimal | None = None,
    spread: Decimal | None = None,
    fixed_years: int | None = None,
    review_months: int = 12,
) -> list[AmortizationRow]:
    """Build the full amortization table.

    Supports three rate types:
    - "fixed"   : constant rate throughout.
    - "variable": Euríbor + spread, payment recalculated every review_months.
    - "mixed"   : fixed rate for the first fixed_years × 12 months,
                  then variable (Euríbor + spread) for the remainder.

    For variable/mixed the Euríbor is treated as a static hypothesis
    (the user's projection). The variable rate is applied as:
        variable_rate = euribor_rate + spread

    Parameters
    ----------
    principal       : loan amount
    annual_rate_pct : initial fixed rate (% p.a.)
    term_years      : total mortgage term in years
    rate_type       : "fixed" | "variable" | "mixed"
    euribor_rate    : Euríbor rate in % (required for variable/mixed)
    spread          : lender spread in % (required for variable/mixed)
    fixed_years     : initial fixed period in years (required for mixed)
    review_months   : review frequency for variable part (12 or 6)
    """
    n_total = term_years * 12
    rows: list[AmortizationRow] = []
    balance = principal

    # Determine the fixed period length (in months)
    fixed_months = 0
    if rate_type == "fixed":
        fixed_months = n_total
    elif rate_type == "mixed":
        fixed_months = (fixed_years or 0) * 12

    # Variable rate (Euríbor + spread)
    variable_rate_pct = Decimal("0")
    if euribor_rate is not None and spread is not None:
        variable_rate_pct = euribor_rate + spread

    # Initial payment for fixed / mixed-fixed period
    current_pmt = _pmt(balance, _monthly_rate(annual_rate_pct), n_total)
    current_rate_pct = annual_rate_pct

    for month in range(1, n_total + 1):
        months_remaining = n_total - month + 1

        # ── Determine applied rate for this month ──────────────────────────
        if rate_type == "fixed":
            applied_rate_pct = annual_rate_pct

        elif rate_type == "variable":
            applied_rate_pct = variable_rate_pct
            # Recalculate payment at every review period
            if (month - 1) % review_months == 0:
                current_pmt = _pmt(
                    balance, _monthly_rate(variable_rate_pct), months_remaining
                )
                current_rate_pct = variable_rate_pct

        else:  # mixed
            if month <= fixed_months:
                applied_rate_pct = annual_rate_pct
                # No recalculation needed during fixed period
            else:
                applied_rate_pct = variable_rate_pct
                # Switch to variable at start of variable period or on review
                months_into_variable = month - fixed_months
                if months_into_variable == 1 or (months_into_variable - 1) % review_months == 0:
                    current_pmt = _pmt(
                        balance, _monthly_rate(variable_rate_pct), months_remaining
                    )
                    current_rate_pct = variable_rate_pct  # noqa: F841

        # ── Calculate breakdown for this month ────────────────────────────
        r = _monthly_rate(applied_rate_pct)
        interest_part = _q2(balance * r)
        # Last payment: pay exactly the remaining balance + interest
        if month == n_total:
            principal_part = _q2(balance)
            payment = _q2(balance + interest_part)
        else:
            payment = current_pmt
            principal_part = _q2(payment - interest_part)
            # Avoid going negative due to rounding
            if principal_part > balance:
                principal_part = _q2(balance)
            payment = _q2(principal_part + interest_part)

        balance = _q2(balance - principal_part)
        if balance < 0:
            balance = Decimal("0.00")

        rows.append(
            AmortizationRow(
                month=month,
                payment=payment,
                principal=principal_part,
                interest=interest_part,
                balance=balance,
                applied_rate=applied_rate_pct,
            )
        )

    return rows


def effective_annual_rate(
    pmt: Decimal,
    principal: Decimal,
    term_years: int,
) -> Decimal:
    """Approximate Effective Annual Rate (TAE) using the nominal monthly rate.

    Uses Newton–Raphson to solve for the monthly rate r that satisfies:
        principal = pmt × [1 − (1+r)^−n] / r

    Falls back to the nominal APR approximation when convergence fails.
    """
    n = term_years * 12
    if principal <= 0 or pmt <= 0 or n == 0:
        return Decimal("0.0000")

    p = float(principal)
    m = float(pmt)

    # Initial guess: nominal monthly rate
    r = m / p / n

    for _ in range(1000):
        if r <= 0:
            r = 1e-8
        f = p - m * (1 - (1 + r) ** (-n)) / r
        df = m * ((1 - (1 + r) ** (-n)) / r**2 - n * (1 + r) ** (-n - 1) / r)
        if df == 0:
            break
        r_new = r - f / df
        if abs(r_new - r) < 1e-10:
            r = r_new
            break
        r = r_new

    tae = (1 + r) ** 12 - 1
    return Decimal(str(round(tae * 100, 4))).quantize(_FOUR, rounding=ROUND_HALF_UP)


def closing_costs(
    property_price: Decimal,
    property_type: str,
    region_tax_rate: Decimal | None = None,
) -> ClosingCostsResult:
    """Calculate mortgage closing costs (gastos de compraventa).

    Parameters
    ----------
    property_price  : purchase price of the property
    property_type   : "new" (obra nueva → AJD) or "second_hand" (segunda mano → ITP)
    region_tax_rate : override for ITP/AJD rate (as percentage, e.g. 8 means 8%).
                      When None, defaults are used: 8 % ITP / 1 % AJD.
    """
    notary = _q2(property_price * _NOTARY_RATE)
    registry = _q2(property_price * _REGISTRY_RATE)
    gestor = _GESTOR_FIXED
    appraisal = _APPRAISAL_FIXED

    if region_tax_rate is not None:
        tax_rate = region_tax_rate / Decimal("100")
    elif property_type == "new":
        tax_rate = _AJD_DEFAULT
    else:
        tax_rate = _ITP_DEFAULT

    tax = _q2(property_price * tax_rate)
    total = _q2(notary + registry + tax + gestor + appraisal)

    return ClosingCostsResult(
        notary=notary,
        registry=registry,
        tax=tax,
        gestor=gestor,
        appraisal=appraisal,
        total=total,
    )
