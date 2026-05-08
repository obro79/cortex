"""add source object content text

Revision ID: 0009_source_object_content_text
Revises: 0008_connector_persistence
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_source_object_content_text"
down_revision: str | None = "0008_connector_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_objects", sa.Column("content_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("source_objects", "content_text")
