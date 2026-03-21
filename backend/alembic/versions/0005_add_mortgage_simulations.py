"""add mortgage simulations

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mortgage_simulations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("property_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("down_payment", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("loan_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("rate_type", sa.String(length=10), nullable=False),
        sa.Column("term_years", sa.Integer(), nullable=False),
        sa.Column("interest_rate", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("euribor_rate", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("spread", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("fixed_years", sa.Integer(), nullable=True),
        sa.Column("review_frequency", sa.String(length=10), nullable=True),
        sa.Column(
            "property_type",
            sa.String(length=15),
            nullable=False,
            server_default="second_hand",
        ),
        sa.Column("region_tax_rate", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column(
            "initial_monthly_payment", sa.Numeric(precision=12, scale=2), nullable=False
        ),
        sa.Column("total_amount_paid", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("total_interest", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mortgage_simulations_user_id"),
        "mortgage_simulations",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_mortgage_simulations_user_id"), table_name="mortgage_simulations"
    )
    op.drop_table("mortgage_simulations")
