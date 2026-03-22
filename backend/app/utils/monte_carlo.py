"""
Funciones puras NumPy para simulaciones Monte Carlo.

No hay dependencias de BD ni async — todo es determinista dado una seed,
o estocástico con distribuciones normales.
"""

from __future__ import annotations

import numpy as np


def simulate_net_distribution(
    income_p50: float,
    income_p10: float,
    income_p90: float,
    expenses_p50: float,
    expenses_p10: float,
    expenses_p90: float,
    n: int = 1000,
    rng: np.random.Generator | None = None,
) -> tuple[float, float, float]:
    """Simula la distribución del neto (ingresos - gastos) con Monte Carlo.

    Estima σ de cada variable a partir del intervalo P10-P90:
        σ = (P90 - P10) / 2.56   (para distribución normal estándar)

    Genera N muestras independientes y devuelve los percentiles del neto
    resultante (net_p10, net_p50, net_p90).

    Args:
        income_p50: Mediana esperada de ingresos.
        income_p10: Percentil 10 de ingresos.
        income_p90: Percentil 90 de ingresos.
        expenses_p50: Mediana esperada de gastos.
        expenses_p10: Percentil 10 de gastos.
        expenses_p90: Percentil 90 de gastos.
        n: Número de simulaciones.
        rng: Generador numpy (opcional, para tests reproducibles).

    Returns:
        (net_p10, net_p50, net_p90)
    """
    if rng is None:
        rng = np.random.default_rng()

    # σ estimado desde el rango intercuantílico P10-P90
    _Z_FACTOR = 2.563_103  # norm.ppf(0.90) - norm.ppf(0.10)
    income_sigma = max((income_p90 - income_p10) / _Z_FACTOR, 0.0)
    expenses_sigma = max((expenses_p90 - expenses_p10) / _Z_FACTOR, 0.0)

    incomes = rng.normal(loc=income_p50, scale=income_sigma, size=n).clip(min=0.0)
    expenses = rng.normal(loc=expenses_p50, scale=expenses_sigma, size=n).clip(min=0.0)
    nets = incomes - expenses

    return (
        float(np.percentile(nets, 10)),
        float(np.percentile(nets, 50)),
        float(np.percentile(nets, 90)),
    )


def apply_scenario_modifications(
    income_p50: float,
    expenses_p50: float,
    salary_variation_pct: float,
    expense_delta_monthly: float,
) -> tuple[float, float]:
    """Aplica variaciones de forma determinista sobre los valores esperados.

    Args:
        income_p50: Mediana de ingresos base.
        expenses_p50: Mediana de gastos base.
        salary_variation_pct: Variación de sueldo en % (ej. 10.0 = +10%).
        expense_delta_monthly: Delta mensual de gastos en euros (puede ser negativo).

    Returns:
        (new_income_p50, new_expenses_p50)
    """
    income_mult = 1.0 + salary_variation_pct / 100.0
    new_income = max(0.0, income_p50 * income_mult)
    new_expenses = max(0.0, expenses_p50 + expense_delta_monthly)
    return new_income, new_expenses
