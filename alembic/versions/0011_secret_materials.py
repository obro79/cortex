"""create encrypted secret material table

Revision ID: 0011_secret_materials
Revises: 0010_scheduler_leases
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_secret_materials"
down_revision: str | None = "0010_scheduler_leases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "secret_materials",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("secret_ref_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("encryption_scheme", sa.String(length=128), nullable=False),
        sa.Column("key_version", sa.String(length=128), nullable=False),
        sa.Column("ciphertext", sa.String(), nullable=False),
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
        sa.UniqueConstraint("secret_ref_id", name="uq_secret_materials_secret_ref"),
    )
    op.create_index(
        "ix_secret_materials_workspace_provider",
        "secret_materials",
        ["workspace_id", "provider"],
    )


def downgrade() -> None:
    op.drop_table("secret_materials")
