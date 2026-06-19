"""add resume storage metadata

Revision ID: a19f2b7e4c63
Revises: f29a4c0d8b71
Create Date: 2026-06-14 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a19f2b7e4c63"
down_revision: Union[str, Sequence[str], None] = "f29a4c0d8b71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("resumes", sa.Column("file_name", sa.Text(), nullable=True))
    op.add_column("resumes", sa.Column("file_mime_type", sa.Text(), nullable=True))
    op.add_column("resumes", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.add_column("resumes", sa.Column("storage_bucket", sa.Text(), nullable=True))
    op.add_column("resumes", sa.Column("storage_path", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("resumes", "storage_path")
    op.drop_column("resumes", "storage_bucket")
    op.drop_column("resumes", "file_size_bytes")
    op.drop_column("resumes", "file_mime_type")
    op.drop_column("resumes", "file_name")
