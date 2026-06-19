"""make resume user unique

Revision ID: d4b6e9a13277
Revises: b7c2a9d8f041
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4b6e9a13277"
down_revision: Union[str, None] = "b7c2a9d8f041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_resumes_user_id", table_name="resumes")
    op.create_index("uq_resumes_user_id", "resumes", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_resumes_user_id", table_name="resumes")
    op.create_index("idx_resumes_user_id", "resumes", ["user_id"], unique=False)
