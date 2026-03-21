"""add investments

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("investment_type", sa.String(length=20), nullable=False),
        sa.Column("principal_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("interest_rate", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("interest_type", sa.String(length=10), nullable=False),
        sa.Column("compounding_frequency", sa.String(length=10), nullable=True),
        sa.Column("current_value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False),
        sa.Column("renewal_period_months", sa.Integer(), nullable=True),
        sa.Column("renewals_count", sa.Integer(), nullable=False),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
            ["account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investments_user_id"), "investments", ["user_id"], unique=False)
    op.create_index(op.f("ix_investments_account_id"), "investments", ["account_id"], unique=False)
    op.create_index(op.f("ix_investments_start_date"), "investments", ["start_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_investments_start_date"), table_name="investments")
    op.drop_index(op.f("ix_investments_account_id"), table_name="investments")
    op.drop_index(op.f("ix_investments_user_id"), table_name="investments")
    op.drop_table("investments")
