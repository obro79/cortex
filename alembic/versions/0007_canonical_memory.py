"""create canonical decision and approval tables

Revision ID: 0007_canonical_memory
Revises: 0006_context_gate_results
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_canonical_memory"
down_revision: str | None = "0006_context_gate_results"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_decisions",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("scope_ref", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("decision_text", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("evidence_pack_id", sa.String(length=128), nullable=True),
        sa.Column("supersedes_decision_id", sa.String(length=128), nullable=True),
        sa.Column("superseded_by_decision_id", sa.String(length=128), nullable=True),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=True),
        sa.Column("approved_by_actor_id", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_citations_json", sa.JSON(), nullable=False),
        sa.Column("stale_or_superseded_evidence_json", sa.JSON(), nullable=False),
        sa.Column("decision_version", sa.String(length=128), nullable=False),
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
        "ix_canonical_decisions_workspace_scope_status",
        "canonical_decisions",
        ["workspace_id", "scope_type", "scope_ref", "status"],
    )
    op.create_index(
        "ix_canonical_decisions_workspace_status_approved",
        "canonical_decisions",
        ["workspace_id", "status", "approved_at"],
    )
    op.create_index(
        "ix_canonical_decisions_workspace_supersedes",
        "canonical_decisions",
        ["workspace_id", "supersedes_decision_id"],
    )

    op.create_table(
        "approval_records",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("original_text", sa.String(), nullable=True),
        sa.Column("final_text", sa.String(), nullable=True),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("evidence_pack_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_approval_records_workspace_target",
        "approval_records",
        ["workspace_id", "target_type", "target_id"],
    )
    op.create_index(
        "ix_approval_records_workspace_actor_created",
        "approval_records",
        ["workspace_id", "actor_id", "created_at"],
    )
    op.create_index(
        "ix_approval_records_workspace_action_created",
        "approval_records",
        ["workspace_id", "action", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_approval_records_workspace_action_created",
        table_name="approval_records",
    )
    op.drop_index(
        "ix_approval_records_workspace_actor_created",
        table_name="approval_records",
    )
    op.drop_index("ix_approval_records_workspace_target", table_name="approval_records")
    op.drop_table("approval_records")
    op.drop_index(
        "ix_canonical_decisions_workspace_supersedes",
        table_name="canonical_decisions",
    )
    op.drop_index(
        "ix_canonical_decisions_workspace_status_approved",
        table_name="canonical_decisions",
    )
    op.drop_index(
        "ix_canonical_decisions_workspace_scope_status",
        table_name="canonical_decisions",
    )
    op.drop_table("canonical_decisions")
