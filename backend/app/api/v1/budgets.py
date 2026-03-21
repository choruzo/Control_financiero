import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.budgets import (
    BudgetAlertResponse,
    BudgetCreate,
    BudgetResponse,
    BudgetStatusResponse,
    BudgetUpdate,
)
from app.services import budgets as budgets_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


# Rutas específicas ANTES de /{budget_id} para evitar conflictos de resolución


@router.get("/alerts", response_model=list[BudgetAlertResponse])
async def list_alerts(
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BudgetAlertResponse]:
    """Lista todas las alertas de presupuesto del usuario."""
    return await budgets_service.list_alerts(db, current_user.id, unread_only)


@router.patch("/alerts/{alert_id}/read", response_model=BudgetAlertResponse)
async def mark_alert_read(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BudgetAlertResponse:
    """Marca una alerta como leída."""
    return await budgets_service.mark_alert_read(db, current_user.id, alert_id)


@router.get("/status", response_model=list[BudgetStatusResponse])
async def list_budget_statuses(
    period_year: int = Query(..., ge=2000, le=2100),
    period_month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BudgetStatusResponse]:
    """Devuelve el estado (gasto vs límite) de todos los presupuestos de un período."""
    return await budgets_service.list_budget_statuses(
        db, current_user.id, period_year, period_month
    )


@router.post("", response_model=BudgetResponse, status_code=201)
async def create_budget(
    body: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Crea un presupuesto mensual para una categoría."""
    return await budgets_service.create_budget(db, current_user.id, body)


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    period_year: int | None = Query(None, ge=2000, le=2100),
    period_month: int | None = Query(None, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BudgetResponse]:
    """Lista presupuestos con filtros opcionales por período."""
    return await budgets_service.list_budgets(db, current_user.id, period_year, period_month)


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Obtiene un presupuesto por ID."""
    return await budgets_service.get_budget(db, current_user.id, budget_id)


@router.get("/{budget_id}/status", response_model=BudgetStatusResponse)
async def get_budget_status(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BudgetStatusResponse:
    """Calcula el estado actual de un presupuesto (gasto vs límite, % consumido)."""
    return await budgets_service.get_budget_status(db, current_user.id, budget_id)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    body: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Actualiza limit_amount, alert_threshold o name de un presupuesto."""
    return await budgets_service.update_budget(db, current_user.id, budget_id, body)


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina un presupuesto y todas sus alertas."""
    await budgets_service.delete_budget(db, current_user.id, budget_id)
