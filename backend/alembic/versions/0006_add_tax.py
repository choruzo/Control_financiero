"""add tax brackets and tax configs

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tax_brackets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("bracket_type", sa.String(length=10), nullable=False),
        sa.Column("min_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("max_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("rate", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tax_brackets_tax_year"), "tax_brackets", ["tax_year"], unique=False
    )

    op.create_table(
        "tax_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("gross_annual_salary", sa.Numeric(precision=14, scale=2), nullable=False),
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
        sa.UniqueConstraint("user_id", "tax_year", name="uq_tax_config_user_year"),
    )
    op.create_index(
        op.f("ix_tax_configs_user_id"), "tax_configs", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tax_configs_user_id"), table_name="tax_configs")
    op.drop_table("tax_configs")
    op.drop_index(op.f("ix_tax_brackets_tax_year"), table_name="tax_brackets")
    op.drop_table("tax_brackets")
