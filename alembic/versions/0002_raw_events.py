"""create raw events table

Revision ID: 0002_raw_events
Revises: 0001_health_checks
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_raw_events"
down_revision: str | None = "0001_health_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_events",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("source_connection_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_event_id", sa.String(length=256), nullable=False),
        sa.Column("event_type", sa.String(length=256), nullable=False),
        sa.Column("external_object_key", sa.String(length=512), nullable=True),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("payload_ref", sa.String(length=512), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("payload_size_bytes", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("last_error_message", sa.String(length=1024), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            "external_event_id",
            name="uq_raw_events_provider_external_event",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_raw_events_idempotency_key",
        ),
    )
    op.create_index(
        "ix_raw_events_workspace_source_received",
        "raw_events",
        ["workspace_id", "source_connection_id", "received_at"],
    )
    op.create_index(
        "ix_raw_events_workspace_status_retry",
        "raw_events",
        ["workspace_id", "status", "next_retry_at"],
    )
    op.create_index(
        "ix_raw_events_workspace_external_object",
        "raw_events",
        ["workspace_id", "external_object_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_events_workspace_external_object", table_name="raw_events")
    op.drop_index("ix_raw_events_workspace_status_retry", table_name="raw_events")
    op.drop_index("ix_raw_events_workspace_source_received", table_name="raw_events")
    op.drop_table("raw_events")
