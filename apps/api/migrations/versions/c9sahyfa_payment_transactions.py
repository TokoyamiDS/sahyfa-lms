"""Add Sahyfa provider-neutral payment transactions.

Revision ID: c9sahyfa_pay
Revises: b1c2d3e4f5a6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9sahyfa_pay"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sahyfa_payment_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("authority", sa.String(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reference_id", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("callback_url", sa.Text(), nullable=False),
        sa.Column("provider_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "authority", name="uq_sahyfa_payment_provider_authority"),
    )
    op.create_index("ix_sahyfa_payment_transaction_provider", "sahyfa_payment_transaction", ["provider"])
    op.create_index("ix_sahyfa_payment_transaction_authority", "sahyfa_payment_transaction", ["authority"])
    op.create_index("ix_sahyfa_payment_transaction_status", "sahyfa_payment_transaction", ["status"])
    op.create_index("ix_sahyfa_payment_user_status", "sahyfa_payment_transaction", ["user_id", "status"])
    op.create_index("ix_sahyfa_payment_org_created", "sahyfa_payment_transaction", ["org_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_sahyfa_payment_org_created", table_name="sahyfa_payment_transaction")
    op.drop_index("ix_sahyfa_payment_user_status", table_name="sahyfa_payment_transaction")
    op.drop_index("ix_sahyfa_payment_transaction_status", table_name="sahyfa_payment_transaction")
    op.drop_index("ix_sahyfa_payment_transaction_authority", table_name="sahyfa_payment_transaction")
    op.drop_index("ix_sahyfa_payment_transaction_provider", table_name="sahyfa_payment_transaction")
    op.drop_table("sahyfa_payment_transaction")
