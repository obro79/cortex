"""add provider principal mappings

Revision ID: 0016_provider_principal_mappings
Revises: 0015_provider_acl_snapshots
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_provider_principal_mappings"
down_revision: str | None = "0015_provider_acl_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_principal_mappings",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("principal_type", sa.String(length=128), nullable=False),
        sa.Column("principal_id_hash", sa.String(length=128), nullable=False),
        sa.Column("match_method", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
            "user_id",
            "provider",
            "principal_type",
            "principal_id_hash",
            name="uq_provider_principal_mapping",
        ),
    )
    op.create_index(
        "ix_provider_principal_mappings_user",
        "provider_principal_mappings",
        ["workspace_id", "user_id", "status", "expires_at"],
    )
    op.create_index(
        "ix_provider_principal_mappings_principal",
        "provider_principal_mappings",
        ["workspace_id", "provider", "principal_type", "principal_id_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_principal_mappings_principal",
        table_name="provider_principal_mappings",
    )
    op.drop_index(
        "ix_provider_principal_mappings_user",
        table_name="provider_principal_mappings",
    )
    op.drop_table("provider_principal_mappings")
