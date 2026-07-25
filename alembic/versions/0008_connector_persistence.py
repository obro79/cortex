"""create provider connector tables

Revision ID: 0008_connector_persistence
Revises: 0007_canonical_memory
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_connector_persistence"
down_revision: str | None = "0007_canonical_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "secret_refs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=128), nullable=False),
        sa.Column("external_secret_id", sa.String(length=512), nullable=False),
        sa.Column("key_version", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
    )
    op.create_index(
        "ix_secret_refs_workspace_provider", "secret_refs", ["workspace_id", "provider"]
    )
    op.create_index(
        "ix_secret_refs_workspace_status", "secret_refs", ["workspace_id", "status"]
    )

    op.create_table(
        "oauth_installations",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_workspace_id", sa.String(length=128), nullable=False),
        sa.Column("enterprise_id", sa.String(length=128), nullable=True),
        sa.Column("bot_user_id", sa.String(length=128), nullable=True),
        sa.Column("installing_actor_id", sa.String(length=128), nullable=True),
        sa.Column("secret_ref_id", sa.String(length=128), nullable=False),
        sa.Column("scopes_json", sa.JSON(), nullable=False),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("health_json", sa.JSON(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
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
            "provider_workspace_id",
            name="uq_oauth_installations_provider_workspace",
        ),
    )
    op.create_index(
        "ix_oauth_installations_workspace_status",
        "oauth_installations",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_oauth_installations_workspace_provider",
        "oauth_installations",
        ["workspace_id", "provider"],
    )

    op.create_table(
        "source_connections",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("oauth_installation_id", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("external_source_id", sa.String(length=256), nullable=False),
        sa.Column("display_name_hash", sa.String(length=128), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=False),
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
            "external_source_id",
            name="uq_source_connections_provider_source",
        ),
    )
    op.create_index(
        "ix_source_connections_workspace_status",
        "source_connections",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_source_connections_workspace_install",
        "source_connections",
        ["workspace_id", "oauth_installation_id"],
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("delivery_id", sa.String(length=256), nullable=False),
        sa.Column("event_id", sa.String(length=256), nullable=True),
        sa.Column("signature_status", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("source_connection_id", sa.String(length=128), nullable=True),
        sa.Column("raw_event_id", sa.String(length=128), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            "delivery_id",
            name="uq_webhook_deliveries_provider_delivery",
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_workspace_status",
        "webhook_deliveries",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_webhook_deliveries_workspace_event",
        "webhook_deliveries",
        ["workspace_id", "event_id"],
    )

    op.create_table(
        "backfill_jobs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source_connection_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("cursor_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
    )
    op.create_index(
        "ix_backfill_jobs_workspace_status", "backfill_jobs", ["workspace_id", "status"]
    )
    op.create_index(
        "ix_backfill_jobs_workspace_source",
        "backfill_jobs",
        ["workspace_id", "source_connection_id"],
    )

    op.create_table(
        "provider_cursors",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source_connection_id", sa.String(length=128), nullable=False),
        sa.Column("cursor_type", sa.String(length=64), nullable=False),
        sa.Column("cursor_value", sa.String(length=256), nullable=True),
        sa.Column("high_watermark", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("last_advanced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
            "source_connection_id",
            "cursor_type",
            name="uq_provider_cursors_identity",
        ),
    )
    op.create_index(
        "ix_provider_cursors_workspace_status",
        "provider_cursors",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_provider_cursors_workspace_source",
        "provider_cursors",
        ["workspace_id", "source_connection_id"],
    )


def downgrade() -> None:
    op.drop_table("provider_cursors")
    op.drop_table("backfill_jobs")
    op.drop_table("webhook_deliveries")
    op.drop_table("source_connections")
    op.drop_table("oauth_installations")
    op.drop_table("secret_refs")
