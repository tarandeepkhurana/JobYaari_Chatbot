"""remove city from jobs

Revision ID: f29a4c0d8b71
Revises: c639b8ea3b10
Create Date: 2026-06-14 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f29a4c0d8b71"
down_revision: Union[str, Sequence[str], None] = "c639b8ea3b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("jobs", "city")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("jobs", sa.Column("city", sa.Text(), nullable=True))
