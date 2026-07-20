"""add immutable redacted demo run report projection

Revision ID: 0020_demo_run_reports
Revises: 0019_provider_acl_current_unique
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_demo_run_reports"
down_revision: str | None = "0019_provider_acl_current_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist validated, content-free controlled-run report snapshots."""
    op.create_table(
        "demo_run_reports",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        # Cortex internal linkage only; no raw Slack/Jira/GitHub resource ID.
        sa.Column("source_connection_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("run_id_hash", sa.String(length=71), nullable=False),
        sa.Column("source_ref_hash", sa.String(length=71), nullable=False),
        sa.Column("collection", sa.String(length=160), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "run_id_hash",
            name="uq_demo_run_reports_workspace_run",
        ),
    )
    op.create_index(
        "ix_demo_run_reports_workspace_completed",
        "demo_run_reports",
        ["workspace_id", "completed_at"],
    )
    op.create_index(
        "ix_demo_run_reports_workspace_source_completed",
        "demo_run_reports",
        ["workspace_id", "source_connection_id", "completed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_demo_run_reports_workspace_source_completed",
        table_name="demo_run_reports",
    )
    op.drop_index(
        "ix_demo_run_reports_workspace_completed", table_name="demo_run_reports"
    )
    op.drop_table("demo_run_reports")
