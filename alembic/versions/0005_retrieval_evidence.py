"""create retrieval request and evidence pack tables

Revision ID: 0005_retrieval_evidence
Revises: 0004_chunking_indexing
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_retrieval_evidence"
down_revision: str | None = "0004_chunking_indexing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retrieval_requests",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("caller_type", sa.String(length=64), nullable=False),
        sa.Column("caller_id", sa.String(length=128), nullable=True),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("task_hints_json", sa.JSON(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column(
            "source_allowlist_snapshot_hash", sa.String(length=128), nullable=True
        ),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
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
        "ix_retrieval_requests_workspace_status",
        "retrieval_requests",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_retrieval_requests_workspace_created",
        "retrieval_requests",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "evidence_packs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("retrieval_request_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("claims_json", sa.JSON(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("candidate_summary_json", sa.JSON(), nullable=False),
        sa.Column("source_coverage_json", sa.JSON(), nullable=False),
        sa.Column("permission_exclusions_json", sa.JSON(), nullable=False),
        sa.Column("missing_context_json", sa.JSON(), nullable=False),
        sa.Column("stale_context_json", sa.JSON(), nullable=False),
        sa.Column("conflict_summary_json", sa.JSON(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=True),
        sa.Column("ranker_version", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_evidence_packs_workspace_status",
        "evidence_packs",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_evidence_packs_workspace_request",
        "evidence_packs",
        ["workspace_id", "retrieval_request_id"],
    )
    op.create_index(
        "ix_evidence_packs_workspace_expires",
        "evidence_packs",
        ["workspace_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_packs_workspace_expires", table_name="evidence_packs")
    op.drop_index("ix_evidence_packs_workspace_request", table_name="evidence_packs")
    op.drop_index("ix_evidence_packs_workspace_status", table_name="evidence_packs")
    op.drop_table("evidence_packs")
    op.drop_index(
        "ix_retrieval_requests_workspace_created", table_name="retrieval_requests"
    )
    op.drop_index(
        "ix_retrieval_requests_workspace_status", table_name="retrieval_requests"
    )
    op.drop_table("retrieval_requests")
