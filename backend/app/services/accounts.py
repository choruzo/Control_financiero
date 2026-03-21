import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.schemas.accounts import AccountCreate, AccountUpdate


async def create_account(db: AsyncSession, user_id: uuid.UUID, data: AccountCreate) -> Account:
    account = Account(
        user_id=user_id,
        name=data.name,
        bank=data.bank,
        account_type=data.account_type.value,
        currency=data.currency.upper(),
        balance=data.balance,
    )
    db.add(account)
    await db.flush()
    return account


async def get_accounts(db: AsyncSession, user_id: uuid.UUID) -> list[Account]:
    result = await db.execute(select(Account).where(Account.user_id == user_id))
    return list(result.scalars().all())


async def get_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


async def update_account(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID, data: AccountUpdate
) -> Account:
    account = await get_account(db, user_id, account_id)
    update_data = data.model_dump(exclude_unset=True)
    if "account_type" in update_data and update_data["account_type"] is not None:
        update_data["account_type"] = update_data["account_type"].value
    for field, value in update_data.items():
        setattr(account, field, value)
    await db.flush()
    return account


async def delete_account(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID
) -> None:
    account = await get_account(db, user_id, account_id)
    await db.delete(account)
    await db.flush()
