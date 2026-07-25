"""create ingestion transactional outbox

Revision ID: 0017_ingestion_outbox
Revises: 0016_provider_principal_mappings
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_ingestion_outbox"
down_revision: str | None = "0016_provider_principal_mappings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_outbox",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("raw_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(length=1024)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("raw_event_id", name="uq_ingestion_outbox_raw_event"),
    )
    op.create_index(
        "ix_ingestion_outbox_due",
        "ingestion_outbox",
        ["status", "next_attempt_at", "created_at"],
    )
    op.create_index(
        "ix_ingestion_outbox_workspace_status",
        "ingestion_outbox",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_outbox_workspace_status", table_name="ingestion_outbox")
    op.drop_index("ix_ingestion_outbox_due", table_name="ingestion_outbox")
    op.drop_table("ingestion_outbox")
