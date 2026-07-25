"""add lifecycle persistence tables

Revision ID: 0013_lifecycle_persistence
Revises: 0012_tenant_identity
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_lifecycle_persistence"
down_revision: str | None = "0012_tenant_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retention_policies",
        sa.Column("workspace_id", sa.String(length=128), primary_key=True),
        sa.Column("raw_event_days", sa.Integer(), nullable=True),
        sa.Column("payload_days", sa.Integer(), nullable=True),
        sa.Column("audit_log_days", sa.Integer(), nullable=True),
        sa.Column("tombstone_days", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_retention_policies_workspace",
        "retention_policies",
        ["workspace_id"],
    )

    op.create_table(
        "deletion_tombstones",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=128), nullable=False),
        sa.Column("target_id_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("requested_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_deletion_tombstones_workspace_status",
        "deletion_tombstones",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_deletion_tombstones_workspace_target",
        "deletion_tombstones",
        ["workspace_id", "target_type", "target_id_hash"],
    )

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("requested_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("export_scope", sa.String(length=128), nullable=False),
        sa.Column("destination_ref", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_export_jobs_workspace_status",
        "export_jobs",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_export_jobs_workspace_created",
        "export_jobs",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_export_jobs_workspace_created", table_name="export_jobs")
    op.drop_index("ix_export_jobs_workspace_status", table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_index(
        "ix_deletion_tombstones_workspace_target",
        table_name="deletion_tombstones",
    )
    op.drop_index(
        "ix_deletion_tombstones_workspace_status",
        table_name="deletion_tombstones",
    )
    op.drop_table("deletion_tombstones")
    op.drop_index(
        "ix_retention_policies_workspace",
        table_name="retention_policies",
    )
    op.drop_table("retention_policies")
