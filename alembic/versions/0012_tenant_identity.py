"""add tenant identity tables

Revision ID: 0012_tenant_identity
Revises: 0011_secret_materials
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_tenant_identity"
down_revision: str | None = "0011_secret_materials"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=128), nullable=True),
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
    op.create_index("ix_organizations_status", "organizations", ["status"])
    op.create_index(
        "ix_organizations_created_by", "organizations", ["created_by_user_id"]
    )

    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=128), nullable=True),
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
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspaces_org_slug"),
    )
    op.create_index(
        "ix_workspaces_organization_status",
        "workspaces",
        ["organization_id", "status"],
    )
    op.create_index("ix_workspaces_created_by", "workspaces", ["created_by_user_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("auth_provider", sa.String(length=64), nullable=False),
        sa.Column("auth_subject", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
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
            "auth_provider", "auth_subject", name="uq_users_auth_provider_subject"
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=128), nullable=True),
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
            "organization_id",
            "workspace_id",
            "user_id",
            name="uq_memberships_scope_user",
        ),
    )
    op.create_index("ix_memberships_user_status", "memberships", ["user_id", "status"])
    op.create_index(
        "ix_memberships_workspace_role", "memberships", ["workspace_id", "role"]
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("accepted_by_user_id", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
    )
    op.create_index(
        "ix_invitations_workspace_status",
        "invitations",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_invitations_email_status", "invitations", ["email", "status"]
    )

    op.create_table(
        "legal_consents",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("consent_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "consent_type", "version", name="uq_legal_consents_user_version"
        ),
    )
    op.create_index(
        "ix_legal_consents_workspace_user",
        "legal_consents",
        ["workspace_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_table("legal_consents")
    op.drop_table("invitations")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("workspaces")
    op.drop_table("organizations")
