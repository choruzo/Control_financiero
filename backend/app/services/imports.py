"""Servicio de importación de transacciones desde archivos CSV."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.imports import ImportResult, ImportRowResult, ImportRowStatus
from app.utils.csv_parser import parse_openbank_csv


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


async def _is_duplicate(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    parsed_row,
) -> bool:
    """Comprueba si ya existe una transacción con los mismos datos clave."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
            Transaction.date == parsed_row.date,
            Transaction.amount == parsed_row.amount,
            Transaction.description == parsed_row.description,
        )
    )
    return result.scalar_one_or_none() is not None


async def import_transactions_from_csv(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    file_content: bytes,
    dry_run: bool = False,
) -> ImportResult:
    """Importa transacciones desde un CSV en formato OpenBank.

    Args:
        db: Sesión async de SQLAlchemy.
        user_id: ID del usuario autenticado.
        account_id: ID de la cuenta destino (debe pertenecer al usuario).
        file_content: Bytes del archivo CSV.
        dry_run: Si True, calcula el resultado sin insertar nada en BD.

    Returns:
        ImportResult con el detalle de cada fila procesada.
    """
    await _verify_account_owner(db, user_id, account_id)

    parsed_rows, parse_errors = parse_openbank_csv(file_content)

    total_rows = len(parsed_rows) + len(parse_errors)
    rows: list[ImportRowResult] = []
    imported = 0
    skipped_duplicates = 0

    # Filas con error de parseo
    for err in parse_errors:
        rows.append(
            ImportRowResult(
                row=err.row_index,
                status=ImportRowStatus.error,
                error_detail=err.error,
            )
        )

    # Filas válidas
    for parsed in parsed_rows:
        transaction_type = "income" if parsed.amount > 0 else "expense"

        duplicate = await _is_duplicate(db, user_id, account_id, parsed)
        if duplicate:
            skipped_duplicates += 1
            rows.append(
                ImportRowResult(
                    row=parsed.row_index,
                    status=ImportRowStatus.skipped_duplicate,
                    description=parsed.description,
                    amount=parsed.amount,
                    date=parsed.date,
                )
            )
            continue

        if not dry_run:
            transaction = Transaction(
                account_id=account_id,
                user_id=user_id,
                category_id=None,
                amount=parsed.amount,
                description=parsed.description,
                transaction_type=transaction_type,
                date=parsed.date,
                is_recurring=False,
                recurrence_rule=None,
                notes=None,
            )
            db.add(transaction)
            await db.flush()
            transaction_id = transaction.id
        else:
            transaction_id = None

        imported += 1
        rows.append(
            ImportRowResult(
                row=parsed.row_index,
                status=ImportRowStatus.imported,
                description=parsed.description,
                amount=parsed.amount,
                date=parsed.date,
                transaction_id=transaction_id,
            )
        )

    # Ordenar filas por row_index para respuesta coherente
    rows.sort(key=lambda r: r.row)

    return ImportResult(
        account_id=account_id,
        dry_run=dry_run,
        total_rows=total_rows,
        imported=imported,
        skipped_duplicates=skipped_duplicates,
        errors=len(parse_errors),
        rows=rows,
    )
