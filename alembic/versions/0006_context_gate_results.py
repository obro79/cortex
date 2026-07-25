"""create context gate result table

Revision ID: 0006_context_gate_results
Revises: 0005_retrieval_evidence
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_context_gate_results"
down_revision: str | None = "0005_retrieval_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "context_gate_results",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("retrieval_request_id", sa.String(length=128), nullable=False),
        sa.Column("evidence_pack_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("risk_category", sa.String(length=128), nullable=True),
        sa.Column("reasons_json", sa.JSON(), nullable=False),
        sa.Column("required_actions_json", sa.JSON(), nullable=False),
        sa.Column("gate_version", sa.String(length=128), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_action", sa.String(length=128), nullable=True),
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
    )
    op.create_index(
        "ix_context_gate_results_workspace_status_evaluated",
        "context_gate_results",
        ["workspace_id", "status", "evaluated_at"],
    )
    op.create_index(
        "ix_context_gate_results_workspace_risk_evaluated",
        "context_gate_results",
        ["workspace_id", "risk_category", "evaluated_at"],
    )
    op.create_index(
        "ix_context_gate_results_workspace_request",
        "context_gate_results",
        ["workspace_id", "retrieval_request_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_context_gate_results_workspace_request",
        table_name="context_gate_results",
    )
    op.drop_index(
        "ix_context_gate_results_workspace_risk_evaluated",
        table_name="context_gate_results",
    )
    op.drop_index(
        "ix_context_gate_results_workspace_status_evaluated",
        table_name="context_gate_results",
    )
    op.drop_table("context_gate_results")
