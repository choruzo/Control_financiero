import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.tax import (
    TaxBracketResponse,
    TaxCalculationResponse,
    TaxConfigCreate,
    TaxConfigResponse,
    TaxConfigUpdate,
)
from app.services import tax as tax_service

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/brackets", response_model=list[TaxBracketResponse])
async def list_brackets(
    year: int | None = Query(None, description="Filter by tax year, e.g. 2025"),
    bracket_type: str | None = Query(None, description="'general' or 'savings'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaxBracketResponse]:
    """List IRPF tax brackets. Filter by year and/or type."""
    return await tax_service.list_brackets(db, year, bracket_type)


@router.post("/configs", response_model=TaxConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_config(
    body: TaxConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxConfigResponse:
    """Create a tax configuration (gross annual salary) for a given year."""
    return await tax_service.create_tax_config(db, current_user.id, body)


@router.get("/configs", response_model=list[TaxConfigResponse])
async def list_tax_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaxConfigResponse]:
    """List all tax configurations for the current user."""
    return await tax_service.list_tax_configs(db, current_user.id)


@router.get("/configs/{config_id}/calculation", response_model=TaxCalculationResponse)
async def get_tax_calculation(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxCalculationResponse:
    """Calculate gross → net breakdown (IRPF + SS) for a saved tax config."""
    return await tax_service.calculate_tax(db, current_user.id, config_id)


@router.get("/configs/{config_id}", response_model=TaxConfigResponse)
async def get_tax_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxConfigResponse:
    """Retrieve a specific tax configuration by ID."""
    return await tax_service.get_tax_config(db, current_user.id, config_id)


@router.patch("/configs/{config_id}", response_model=TaxConfigResponse)
async def update_tax_config(
    config_id: uuid.UUID,
    body: TaxConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaxConfigResponse:
    """Update the gross salary of an existing tax configuration."""
    return await tax_service.update_tax_config(db, current_user.id, config_id, body)


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tax configuration."""
    await tax_service.delete_tax_config(db, current_user.id, config_id)
