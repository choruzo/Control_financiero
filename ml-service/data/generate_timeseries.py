"""
Generador de series temporales sintéticas de cashflow para España.

Simula perfiles de usuarios con patrones realistas:
- Salario base mensual con pagas extra en junio y diciembre
- Gastos con estacionalidad (verano +15%, navidad +20%)
- Ruido gaussiano para variabilidad natural
- Tendencias de ahorro a largo plazo

Uso:
    python data/generate_timeseries.py
    # Genera ml-service/data/timeseries_dataset.json
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

SERIES_PER_PROFILE = 40
MONTHS_PER_SERIES = 36
SEED = 42

rng = np.random.default_rng(SEED)


def _seasonal_expense_factor(month: int) -> float:
    """Factor multiplicador de gastos según mes (1=enero, 12=diciembre)."""
    # Verano (julio-agosto): +15% por vacaciones
    if month in (7, 8):
        return 1.15
    # Navidad (diciembre): +20% por regalos, cenas
    if month == 12:
        return 1.20
    # Septiembre: +10% (vuelta al cole, seguro coche)
    if month == 9:
        return 1.10
    return 1.0


def _income_factor(month: int) -> float:
    """Factor de ingresos según mes (pagas extra en junio y diciembre)."""
    if month in (6, 12):
        return 2.0  # paga doble
    return 1.0


def _generate_series(
    base_income: float,
    expense_ratio: float,
    income_noise: float = 0.03,
    expense_noise: float = 0.05,
    start_month: int = 1,
    start_year: int = 2023,
) -> list[list[float]]:
    """
    Genera una serie de MONTHS_PER_SERIES meses de (income, expenses).

    Args:
        base_income: Salario mensual base en euros
        expense_ratio: Fracción del salario mensual base destinada a gastos
        income_noise: Desviación estándar relativa del ruido en ingresos
        expense_noise: Desviación estándar relativa del ruido en gastos
        start_month: Mes de inicio (1-12)
        start_year: Año de inicio

    Returns:
        Lista de [income, expenses] para cada mes
    """
    series: list[list[float]] = []
    month, year = start_month, start_year

    for _ in range(MONTHS_PER_SERIES):
        # Ingresos: salario base con factor paga extra + ruido
        income = (
            base_income
            * _income_factor(month)
            * (1.0 + rng.normal(0, income_noise))
        )
        income = max(0.0, income)

        # Gastos: base mensual con estacionalidad + ruido
        monthly_expenses_base = base_income * expense_ratio
        expenses = (
            monthly_expenses_base
            * _seasonal_expense_factor(month)
            * (1.0 + rng.normal(0, expense_noise))
        )
        expenses = max(0.0, expenses)

        series.append([round(income, 2), round(expenses, 2)])

        month += 1
        if month > 12:
            month = 1
            year += 1

    return series


def generate_dataset() -> list[list[list[float]]]:
    """Genera el dataset completo con múltiples perfiles."""
    dataset: list[list[list[float]]] = []

    # Perfil 1: Asalariado bajo (1.800€/mes), ahorro ajustado
    for _ in range(SERIES_PER_PROFILE):
        base = rng.uniform(1500, 2200)
        ratio = rng.uniform(0.75, 0.90)
        start_m = int(rng.integers(1, 13))
        dataset.append(_generate_series(base, ratio, start_month=start_m))

    # Perfil 2: Asalariado medio (2.800€/mes), buen ahorro
    for _ in range(SERIES_PER_PROFILE):
        base = rng.uniform(2400, 3200)
        ratio = rng.uniform(0.60, 0.75)
        start_m = int(rng.integers(1, 13))
        dataset.append(_generate_series(base, ratio, start_month=start_m))

    # Perfil 3: Asalariado alto (4.500€/mes), alto ahorro
    for _ in range(SERIES_PER_PROFILE):
        base = rng.uniform(3800, 5500)
        ratio = rng.uniform(0.50, 0.65)
        start_m = int(rng.integers(1, 13))
        dataset.append(_generate_series(base, ratio, start_month=start_m))

    # Perfil 4: Autónomo (ingresos variables, gastos estables)
    for _ in range(SERIES_PER_PROFILE):
        base = rng.uniform(2000, 4000)
        ratio = rng.uniform(0.55, 0.80)
        start_m = int(rng.integers(1, 13))
        # Mayor variabilidad en ingresos para autónomos
        dataset.append(
            _generate_series(base, ratio, income_noise=0.15, start_month=start_m)
        )

    # Perfil 5: Pareja (ingresos dobles, gastos compartidos)
    for _ in range(SERIES_PER_PROFILE):
        base = rng.uniform(3500, 6000)
        ratio = rng.uniform(0.55, 0.70)
        start_m = int(rng.integers(1, 13))
        dataset.append(_generate_series(base, ratio, start_month=start_m))

    return dataset


if __name__ == "__main__":
    output_path = Path(__file__).parent / "timeseries_dataset.json"
    dataset = generate_dataset()
    output_path.write_text(json.dumps(dataset, indent=None), encoding="utf-8")
    total_examples = sum(
        max(0, len(s) - 12) for s in dataset
    )
    print(f"Dataset generado: {len(dataset)} series → {total_examples} ejemplos de entrenamiento")
    print(f"Guardado en: {output_path}")
