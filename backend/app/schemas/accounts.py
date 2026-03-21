import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    investment = "investment"
    credit = "credit"


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bank: str = Field(..., min_length=1, max_length=100)
    account_type: AccountType
    currency: str = Field("EUR", min_length=3, max_length=3)
    balance: Decimal = Field(Decimal("0"), decimal_places=2)


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    bank: str | None = Field(None, min_length=1, max_length=100)
    account_type: AccountType | None = None
    currency: str | None = Field(None, min_length=3, max_length=3)
    balance: Decimal | None = Field(None, decimal_places=2)
    is_active: bool | None = None


class AccountResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    bank: str
    account_type: str
    currency: str
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
