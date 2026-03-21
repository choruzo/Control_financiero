import uuid
from decimal import Decimal

import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transactions import TransactionCreate, TransactionFilters, TransactionResponse, TransactionUpdate

logger = structlog.get_logger(__name__)


async def _verify_account_owner(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID
) -> Account:
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


async def _verify_category_accessible(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            or_(Category.user_id == user_id, Category.is_system.is_(True)),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


async def create_transaction(
    db: AsyncSession, user_id: uuid.UUID, data: TransactionCreate
) -> Transaction:
    await _verify_account_owner(db, user_id, data.account_id)
    if data.category_id is not None:
        await _verify_category_accessible(db, user_id, data.category_id)

    transaction = Transaction(
        account_id=data.account_id,
        user_id=user_id,
        category_id=data.category_id,
        amount=data.amount,
        description=data.description,
        transaction_type=data.transaction_type.value,
        date=data.date,
        is_recurring=data.is_recurring,
        recurrence_rule=data.recurrence_rule.value if data.recurrence_rule else None,
        notes=data.notes,
    )
    db.add(transaction)
    await db.flush()
    return transaction


async def create_transaction_with_ml(
    db: AsyncSession, user_id: uuid.UUID, data: TransactionCreate
) -> TransactionResponse:
    """
    Crea una transacción e intenta auto-categorizar via ML cuando no se
    proporciona category_id.

    - Confianza >= 0.85: auto-asigna la categoría.
    - Confianza >= 0.5: devuelve sugerencia en ml_suggested_category_id/ml_confidence.
    - ML no disponible o confianza baja: crea sin categoría, sin campos ML.
    """
    transaction = await create_transaction(db, user_id, data)

    ml_suggested_category_id: uuid.UUID | None = None
    ml_confidence: float | None = None

    if data.category_id is None:
        try:
            from app.config import settings
            from app.services.ml_client import MLClient

            ml_client = MLClient(base_url=settings.ml_service_url)
            prediction = await ml_client.predict(description=data.description)

            if prediction.ml_available and prediction.category_name:
                cat_result = await db.execute(
                    select(Category).where(
                        Category.name == prediction.category_name,
                        Category.is_system.is_(True),
                    )
                )
                category = cat_result.scalar_one_or_none()

                if category:
                    if prediction.auto_assigned:
                        transaction.category_id = category.id
                        await db.flush()
                        logger.info(
                            "ml_auto_assigned",
                            transaction_id=str(transaction.id),
                            category=prediction.category_name,
                            confidence=prediction.confidence,
                        )
                    elif prediction.suggested:
                        ml_suggested_category_id = category.id
                        ml_confidence = prediction.confidence
                        logger.info(
                            "ml_suggested",
                            transaction_id=str(transaction.id),
                            category=prediction.category_name,
                            confidence=prediction.confidence,
                        )
        except Exception as exc:
            logger.warning("ml_categorization_failed", error=str(exc))

    return TransactionResponse(
        id=transaction.id,
        account_id=transaction.account_id,
        user_id=transaction.user_id,
        category_id=transaction.category_id,
        amount=transaction.amount,
        description=transaction.description,
        transaction_type=transaction.transaction_type,
        date=transaction.date,
        is_recurring=transaction.is_recurring,
        recurrence_rule=transaction.recurrence_rule,
        notes=transaction.notes,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        ml_suggested_category_id=ml_suggested_category_id,
        ml_confidence=ml_confidence,
    )


async def get_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    filters: TransactionFilters,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Transaction], int]:
    query = select(Transaction).where(Transaction.user_id == user_id)

    if filters.date_from is not None:
        query = query.where(Transaction.date >= filters.date_from)
    if filters.date_to is not None:
        query = query.where(Transaction.date <= filters.date_to)
    if filters.category_id is not None:
        query = query.where(Transaction.category_id == filters.category_id)
    if filters.account_id is not None:
        query = query.where(Transaction.account_id == filters.account_id)
    if filters.transaction_type is not None:
        query = query.where(Transaction.transaction_type == filters.transaction_type.value)
    if filters.min_amount is not None:
        query = query.where(Transaction.amount >= filters.min_amount)
    if filters.max_amount is not None:
        query = query.where(Transaction.amount <= filters.max_amount)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    query = query.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_transaction(
    db: AsyncSession, user_id: uuid.UUID, transaction_id: uuid.UUID
) -> Transaction:
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return transaction


async def update_transaction(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    data: TransactionUpdate,
) -> Transaction:
    transaction = await get_transaction(db, user_id, transaction_id)
    update_data = data.model_dump(exclude_unset=True)

    if "category_id" in update_data and update_data["category_id"] is not None:
        await _verify_category_accessible(db, user_id, update_data["category_id"])
    if "transaction_type" in update_data and update_data["transaction_type"] is not None:
        update_data["transaction_type"] = update_data["transaction_type"].value
    if "recurrence_rule" in update_data and update_data["recurrence_rule"] is not None:
        update_data["recurrence_rule"] = update_data["recurrence_rule"].value

    for field, value in update_data.items():
        setattr(transaction, field, value)
    await db.flush()
    return transaction


async def delete_transaction(
    db: AsyncSession, user_id: uuid.UUID, transaction_id: uuid.UUID
) -> None:
    transaction = await get_transaction(db, user_id, transaction_id)
    await db.delete(transaction)
    await db.flush()
