"""add provider acl snapshot tables

Revision ID: 0015_provider_acl_snapshots
Revises: 0014_billing_persistence
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_provider_acl_snapshots"
down_revision: str | None = "0014_billing_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_acl_snapshots",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_id_hash", sa.String(length=128), nullable=False),
        sa.Column("source_connection_id", sa.String(length=128), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_provider_acl_snapshots_current",
        "provider_acl_snapshots",
        [
            "workspace_id",
            "provider",
            "resource_type",
            "resource_id_hash",
            "is_current",
        ],
    )
    op.create_index(
        "ix_provider_acl_snapshots_expires",
        "provider_acl_snapshots",
        ["workspace_id", "expires_at"],
    )

    op.create_table(
        "provider_acl_entries",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_id_hash", sa.String(length=128), nullable=False),
        sa.Column("principal_type", sa.String(length=128), nullable=False),
        sa.Column("principal_id_hash", sa.String(length=128), nullable=False),
        sa.Column("permission", sa.String(length=64), nullable=False),
        sa.Column("effect", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_provider_acl_entries_snapshot",
        "provider_acl_entries",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_provider_acl_entries_principal",
        "provider_acl_entries",
        ["workspace_id", "provider", "principal_type", "principal_id_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_acl_entries_principal",
        table_name="provider_acl_entries",
    )
    op.drop_index(
        "ix_provider_acl_entries_snapshot",
        table_name="provider_acl_entries",
    )
    op.drop_table("provider_acl_entries")
    op.drop_index(
        "ix_provider_acl_snapshots_expires",
        table_name="provider_acl_snapshots",
    )
    op.drop_index(
        "ix_provider_acl_snapshots_current",
        table_name="provider_acl_snapshots",
    )
    op.drop_table("provider_acl_snapshots")
