import uuid
from datetime import date as Date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.imports import ImportResult
from app.schemas.transactions import (
    PaginatedTransactions,
    TransactionCreate,
    TransactionFilters,
    TransactionResponse,
    TransactionType,
    TransactionUpdate,
)
from app.services import imports as imports_service
from app.services import transactions as transactions_service

router = APIRouter(prefix="/transactions", tags=["transactions"])

MAX_CSV_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/import/csv", response_model=ImportResult)
async def import_csv(
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    dry_run: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportResult:
    """Importa transacciones desde un CSV en formato OpenBank.

    - **account_id**: ID de la cuenta destino (debe pertenecer al usuario).
    - **dry_run**: Si True, previsualiza el resultado sin insertar en base de datos.
    """
    content = await file.read(MAX_CSV_SIZE + 1)
    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo supera el límite de 5 MB",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío",
        )
    return await imports_service.import_transactions_from_csv(
        db, current_user.id, account_id, content, dry_run
    )


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Crea una transacción. Si no se indica category_id, el servicio ML intentará categorizarla automáticamente."""
    return await transactions_service.create_transaction_with_ml(db, current_user.id, body)


@router.get("", response_model=PaginatedTransactions)
async def list_transactions(
    date_from: Date | None = Query(None),
    date_to: Date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    account_id: uuid.UUID | None = Query(None),
    transaction_type: TransactionType | None = Query(None),
    min_amount: Decimal | None = Query(None),
    max_amount: Decimal | None = Query(None),
    search: str | None = Query(None, description="Buscar en descripción y notas"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTransactions:
    """List transactions with optional filters and pagination."""
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        account_id=account_id,
        transaction_type=transaction_type,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )
    items, total = await transactions_service.get_transactions(
        db, current_user.id, filters, page, per_page
    )
    return PaginatedTransactions.build(items, total, page, per_page)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Get a single transaction by ID."""
    return await transactions_service.get_transaction(db, current_user.id, transaction_id)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    body: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Partially update a transaction."""
    return await transactions_service.update_transaction(
        db, current_user.id, transaction_id, body
    )


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a transaction."""
    await transactions_service.delete_transaction(db, current_user.id, transaction_id)
