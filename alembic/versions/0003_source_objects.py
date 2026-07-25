"""create source object normalization tables

Revision ID: 0003_source_objects
Revises: 0002_raw_events
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_source_objects"
down_revision: str | None = "0002_raw_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_objects",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("source_connection_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("object_type", sa.String(length=128), nullable=False),
        sa.Column("external_object_id", sa.String(length=256), nullable=False),
        sa.Column("external_object_key", sa.String(length=512), nullable=False),
        sa.Column("parent_object_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("canonical_url", sa.String(length=1024), nullable=True),
        sa.Column("author_external_id", sa.String(length=256), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_version", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("superseded_by_id", sa.String(length=128), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            "object_type",
            "external_object_id",
            name="uq_source_objects_external_identity",
        ),
    )
    op.create_index(
        "ix_source_objects_workspace_external_key",
        "source_objects",
        ["workspace_id", "external_object_key"],
    )
    op.create_index(
        "ix_source_objects_workspace_type_updated",
        "source_objects",
        ["workspace_id", "object_type", "source_updated_at"],
    )
    op.create_index(
        "ix_source_objects_workspace_status",
        "source_objects",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_source_objects_workspace_content_hash",
        "source_objects",
        ["workspace_id", "content_hash"],
    )

    op.create_table(
        "source_files",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("source_object_id", sa.String(length=128), nullable=True),
        sa.Column("source_connection_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_file_id", sa.String(length=256), nullable=False),
        sa.Column("external_object_key", sa.String(length=512), nullable=True),
        sa.Column("file_name_hash", sa.String(length=128), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("storage_ref", sa.String(length=512), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("ocr_text", sa.String(), nullable=True),
        sa.Column("ocr_text_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            "external_file_id",
            name="uq_source_files_external_file",
        ),
    )
    op.create_index(
        "ix_source_files_workspace_object",
        "source_files",
        ["workspace_id", "source_object_id"],
    )
    op.create_index(
        "ix_source_files_workspace_external_key",
        "source_files",
        ["workspace_id", "external_object_key"],
    )
    op.create_index(
        "ix_source_files_workspace_status",
        "source_files",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_source_files_workspace_content_hash",
        "source_files",
        ["workspace_id", "content_hash"],
    )

    op.create_table(
        "relationship_seeds",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("relationship_type", sa.String(length=128), nullable=False),
        sa.Column("from_id", sa.String(length=128), nullable=False),
        sa.Column("to_id", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("raw_event_id", sa.String(length=128), nullable=False),
        sa.Column("normalized_version", sa.String(length=128), nullable=False),
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
        sa.UniqueConstraint(
            "workspace_id",
            "relationship_type",
            "from_id",
            "to_id",
            "normalized_version",
            name="uq_relationship_seeds_identity",
        ),
    )
    op.create_index(
        "ix_relationship_seeds_workspace_from",
        "relationship_seeds",
        ["workspace_id", "from_id"],
    )
    op.create_index(
        "ix_relationship_seeds_workspace_to",
        "relationship_seeds",
        ["workspace_id", "to_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_relationship_seeds_workspace_to", table_name="relationship_seeds")
    op.drop_index(
        "ix_relationship_seeds_workspace_from", table_name="relationship_seeds"
    )
    op.drop_table("relationship_seeds")
    op.drop_index("ix_source_files_workspace_content_hash", table_name="source_files")
    op.drop_index("ix_source_files_workspace_status", table_name="source_files")
    op.drop_index("ix_source_files_workspace_external_key", table_name="source_files")
    op.drop_index("ix_source_files_workspace_object", table_name="source_files")
    op.drop_table("source_files")
    op.drop_index(
        "ix_source_objects_workspace_content_hash", table_name="source_objects"
    )
    op.drop_index("ix_source_objects_workspace_status", table_name="source_objects")
    op.drop_index(
        "ix_source_objects_workspace_type_updated", table_name="source_objects"
    )
    op.drop_index(
        "ix_source_objects_workspace_external_key", table_name="source_objects"
    )
    op.drop_table("source_objects")
