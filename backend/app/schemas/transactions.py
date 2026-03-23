import uuid
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from math import ceil

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"


class RecurrenceRule(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class TransactionCreate(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    amount: Decimal = Field(..., decimal_places=2)
    description: str = Field(..., min_length=1, max_length=255)
    transaction_type: TransactionType
    date: Date
    is_recurring: bool = False
    recurrence_rule: RecurrenceRule | None = None
    notes: str | None = None


class TransactionUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    amount: Decimal | None = Field(None, decimal_places=2)
    description: str | None = Field(None, min_length=1, max_length=255)
    transaction_type: TransactionType | None = None
    date: Date | None = None
    is_recurring: bool | None = None
    recurrence_rule: RecurrenceRule | None = None
    notes: str | None = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID | None
    amount: Decimal
    description: str
    transaction_type: str
    date: Date
    is_recurring: bool
    recurrence_rule: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # Campos ML: presentes solo en POST /transactions cuando el modelo sugiere categoría
    ml_suggested_category_id: uuid.UUID | None = None
    ml_confidence: float | None = None

    model_config = {"from_attributes": True}


class TransactionFilters(BaseModel):
    date_from: Date | None = None
    date_to: Date | None = None
    category_id: uuid.UUID | None = None
    account_id: uuid.UUID | None = None
    transaction_type: TransactionType | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    search: str | None = None


class PaginatedTransactions(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def build(cls, items: list, total: int, page: int, per_page: int) -> "PaginatedTransactions":
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=ceil(total / per_page) if per_page > 0 else 0,
        )
