"""add budgets and budget_alerts

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("limit_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("alert_threshold", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
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
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "period_year",
            "period_month",
            name="uq_budget_user_category_period",
        ),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"], unique=False)
    op.create_index("ix_budgets_category_id", "budgets", ["category_id"], unique=False)
    op.create_index(
        "ix_budgets_period",
        "budgets",
        ["user_id", "period_year", "period_month"],
        unique=False,
    )

    op.create_table(
        "budget_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("spent_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("percentage", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_budget_alerts_budget_id", "budget_alerts", ["budget_id"], unique=False
    )
    op.create_index(
        "ix_budget_alerts_is_read", "budget_alerts", ["is_read"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_budget_alerts_is_read", table_name="budget_alerts")
    op.drop_index("ix_budget_alerts_budget_id", table_name="budget_alerts")
    op.drop_table("budget_alerts")

    op.drop_index("ix_budgets_period", table_name="budgets")
    op.drop_index("ix_budgets_category_id", table_name="budgets")
    op.drop_index("ix_budgets_user_id", table_name="budgets")
    op.drop_table("budgets")
