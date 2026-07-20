"""add durable permission scopes

Revision ID: 0018_permission_scopes
Revises: 0017_ingestion_outbox
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_permission_scopes"
down_revision: str | None = "0017_ingestion_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "permission_scopes",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=128), nullable=False),
        # Only a one-way digest of provider resource identifiers is persisted.
        sa.Column("external_id_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128)),
        sa.Column("removed_by_actor_id", sa.String(length=128)),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
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
            "scope_type",
            "external_id_hash",
            name="uq_permission_scopes_identity",
        ),
    )
    op.create_index(
        "ix_permission_scopes_workspace_status",
        "permission_scopes",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_permission_scopes_workspace_status", table_name="permission_scopes"
    )
    op.drop_table("permission_scopes")
