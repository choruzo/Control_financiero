"""Schemas Pydantic para importación de transacciones desde CSV."""

import datetime
import uuid
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class ImportRowStatus(StrEnum):
    imported = "imported"
    skipped_duplicate = "skipped_duplicate"
    error = "error"


class ImportRowResult(BaseModel):
    row: int
    status: ImportRowStatus
    description: str | None = None
    amount: Decimal | None = None
    date: datetime.date | None = None
    transaction_id: uuid.UUID | None = None  # solo si status=imported y dry_run=False
    error_detail: str | None = None  # solo si status=error


class ImportResult(BaseModel):
    account_id: uuid.UUID
    dry_run: bool
    total_rows: int
    imported: int
    skipped_duplicates: int
    errors: int
    rows: list[ImportRowResult]
