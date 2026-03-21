from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class MortgageSimulation(Base):
    __tablename__ = "mortgage_simulations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Human-readable name given by the user
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # ── Input parameters ──────────────────────────────────────────────────────
    property_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    down_payment: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    loan_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # "fixed" | "variable" | "mixed"
    rate_type: Mapped[str] = mapped_column(String(10), nullable=False)
    term_years: Mapped[int] = mapped_column(Integer, nullable=False)

    # Annual rate % for fixed / mixed-fixed period — NULL for pure variable
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    # Euríbor % — NULL for pure fixed
    euribor_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    # Lender spread % — NULL for pure fixed
    spread: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    # Fixed-rate period in years — only for mixed
    fixed_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "annual" | "semiannual" — only for variable/mixed
    review_frequency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # "new" | "second_hand"
    property_type: Mapped[str] = mapped_column(String(15), nullable=False, default="second_hand")
    # ITP/AJD override in % (NULL = use defaults)
    region_tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)

    # ── Pre-calculated results (summary) ──────────────────────────────────────
    initial_monthly_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_interest: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

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

    user: Mapped[User] = relationship("User", back_populates="mortgage_simulations")
