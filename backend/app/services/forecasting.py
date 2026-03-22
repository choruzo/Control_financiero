"""
Servicio de predicción de flujo de caja.

Orquesta la obtención de datos históricos desde analytics y la llamada
al ml-service para obtener las predicciones LSTM/Prophet.

Degradación graceful: si el ml-service no está disponible, devuelve una
respuesta indicando ml_available=False sin lanzar excepción.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import structlog

from app.schemas.forecasting import CashflowForecastResponse, ForecastMonthResponse
from app.services import analytics as analytics_service
from app.services.ml_client import ml_client

logger = structlog.get_logger(__name__)

_MIN_MONTHS_HISTORY = 1  # mínimo para llamar al ml-service


async def get_cashflow_forecast(
    db,
    user_id: uuid.UUID,
    months_ahead: int = 6,
) -> CashflowForecastResponse:
    """
    Obtiene la predicción de cashflow para los próximos N meses.

    1. Recupera los últimos 24 meses de datos reales via analytics
    2. Envía al ml-service para inferencia LSTM/Prophet
    3. Devuelve respuesta formateada con intervalos de confianza
    """
    # Obtener historial (hasta 24 meses)
    cashflow = await analytics_service.get_cashflow(db, user_id, months=24)

    # Filtrar meses con datos reales (al menos income o expenses > 0)
    historical = [
        {
            "year": m.year,
            "month": m.month,
            "income": float(m.total_income),
            "expenses": float(m.total_expenses),
        }
        for m in cashflow
        if m.total_income > Decimal("0") or m.total_expenses > Decimal("0")
    ]

    if len(historical) < _MIN_MONTHS_HISTORY:
        logger.info(
            "forecast_no_historical_data",
            user_id=str(user_id),
            available_months=len(historical),
        )
        return _empty_response(months_ahead)

    result = await ml_client.forecast(historical_data=historical, months_ahead=months_ahead)

    if not result.ml_available:
        logger.warning("forecast_ml_unavailable", user_id=str(user_id))
        return CashflowForecastResponse(
            predictions=[
                ForecastMonthResponse(**_point_to_decimal(p.model_dump()))
                for p in result.predictions
            ],
            model_used=result.model_used,
            model_version=result.model_version,
            historical_months_used=len(historical),
            ml_available=False,
        )

    predictions = [
        ForecastMonthResponse(**_point_to_decimal(p.model_dump()))
        for p in result.predictions
    ]

    logger.info(
        "forecast_completed",
        user_id=str(user_id),
        months_ahead=months_ahead,
        model_used=result.model_used,
        historical_months=len(historical),
    )

    return CashflowForecastResponse(
        predictions=predictions,
        model_used=result.model_used,
        model_version=result.model_version,
        historical_months_used=len(historical),
        ml_available=True,
    )


def _point_to_decimal(point: dict) -> dict:
    """Convierte los valores float de un ForecastPoint a Decimal."""
    decimal_fields = {
        "income_p10", "income_p50", "income_p90",
        "expenses_p10", "expenses_p50", "expenses_p90",
        "net_p10", "net_p50", "net_p90",
    }
    return {
        k: Decimal(str(round(v, 2))) if k in decimal_fields else v
        for k, v in point.items()
    }


def _empty_response(months_ahead: int) -> CashflowForecastResponse:
    """Respuesta vacía cuando no hay datos históricos suficientes."""
    from datetime import UTC, datetime

    today = datetime.now(UTC).date()
    y, m = today.year, today.month
    months: list[tuple[int, int]] = []
    for _ in range(months_ahead):
        m += 1
        if m > 12:
            m = 1
            y += 1
        months.append((y, m))

    zero = Decimal("0.00")
    predictions = [
        ForecastMonthResponse(
            year=yr, month=mo,
            income_p10=zero, income_p50=zero, income_p90=zero,
            expenses_p10=zero, expenses_p50=zero, expenses_p90=zero,
            net_p10=zero, net_p50=zero, net_p90=zero,
        )
        for yr, mo in months
    ]
    return CashflowForecastResponse(
        predictions=predictions,
        model_used="degraded",
        model_version="unavailable",
        historical_months_used=0,
        ml_available=False,
    )
