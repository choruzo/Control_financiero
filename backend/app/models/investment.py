from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # "deposit" | "fund" | "stock" | "bond"
    investment_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Financial data
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Annual interest rate stored as percentage, e.g. 4.2500 means 4.25%
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    # "simple" | "compound"
    interest_type: Mapped[str] = mapped_column(String(10), nullable=False)
    # "annually" | "quarterly" | "monthly" — required when interest_type="compound"
    compounding_frequency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Last manually set market value; NULL means calculate on the fly from interest formulas
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Lifecycle
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Months to extend on renewal, e.g. 3, 6, 12
    renewal_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renewals_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship("User", back_populates="investments")
    account: Mapped[Account | None] = relationship("Account")
