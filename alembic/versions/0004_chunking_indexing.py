"""create chunking and indexing tables

Revision ID: 0004_chunking_indexing
Revises: 0003_source_objects
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_chunking_indexing"
down_revision: str | None = "0003_source_objects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_chunks",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("source_object_id", sa.String(length=128), nullable=False),
        sa.Column("source_file_id", sa.String(length=128), nullable=True),
        sa.Column("chunk_type", sa.String(length=128), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("text_hash", sa.String(length=128), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("chunking_version", sa.String(length=128), nullable=False),
        sa.Column("citation_label", sa.String(length=512), nullable=True),
        sa.Column("citation_url", sa.String(length=1024), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_from_hash", sa.String(length=128), nullable=True),
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
            "source_object_id",
            "source_file_id",
            "chunk_type",
            "chunk_index",
            "chunking_version",
            name="uq_source_chunks_identity",
        ),
    )
    op.create_index(
        "ix_source_chunks_workspace_status_version",
        "source_chunks",
        ["workspace_id", "status", "chunking_version"],
    )
    op.create_index(
        "ix_source_chunks_workspace_object",
        "source_chunks",
        ["workspace_id", "source_object_id"],
    )
    op.create_index(
        "ix_source_chunks_workspace_file",
        "source_chunks",
        ["workspace_id", "source_file_id"],
    )
    op.create_index(
        "ix_source_chunks_workspace_text_hash",
        "source_chunks",
        ["workspace_id", "text_hash"],
    )
    op.create_index(
        "ix_source_chunks_text_fts",
        "source_chunks",
        [sa.text("to_tsvector('english', text)")],
        postgresql_using="gin",
    )

    op.create_table(
        "embedding_records",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("source_chunk_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=128), nullable=True),
        sa.Column("embedding_version", sa.String(length=128), nullable=False),
        sa.Column("chunking_version", sa.String(length=128), nullable=False),
        sa.Column("input_text_hash", sa.String(length=128), nullable=False),
        sa.Column("vector_hash", sa.String(length=128), nullable=True),
        sa.Column("qdrant_collection", sa.String(length=128), nullable=True),
        sa.Column("qdrant_point_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("model_invocation_id", sa.String(length=128), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("last_error_message", sa.String(length=1024), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
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
            "source_chunk_id",
            "embedding_version",
            name="uq_embedding_records_chunk_version",
        ),
    )
    op.create_index(
        "ix_embedding_records_workspace_status",
        "embedding_records",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_embedding_records_workspace_chunk",
        "embedding_records",
        ["workspace_id", "source_chunk_id"],
    )
    op.create_index(
        "ix_embedding_records_workspace_input_hash",
        "embedding_records",
        ["workspace_id", "input_text_hash"],
    )

    op.create_table(
        "index_jobs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("target_store", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("index_version", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("last_error_message", sa.String(length=1024), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
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
            "target_store",
            "target_type",
            "target_id",
            "operation",
            "index_version",
            name="uq_index_jobs_identity",
        ),
    )
    op.create_index(
        "ix_index_jobs_workspace_status",
        "index_jobs",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_index_jobs_workspace_target",
        "index_jobs",
        ["workspace_id", "target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_index_jobs_workspace_target", table_name="index_jobs")
    op.drop_index("ix_index_jobs_workspace_status", table_name="index_jobs")
    op.drop_table("index_jobs")
    op.drop_index(
        "ix_embedding_records_workspace_input_hash", table_name="embedding_records"
    )
    op.drop_index(
        "ix_embedding_records_workspace_chunk", table_name="embedding_records"
    )
    op.drop_index(
        "ix_embedding_records_workspace_status", table_name="embedding_records"
    )
    op.drop_table("embedding_records")
    op.drop_index("ix_source_chunks_text_fts", table_name="source_chunks")
    op.drop_index("ix_source_chunks_workspace_text_hash", table_name="source_chunks")
    op.drop_index("ix_source_chunks_workspace_file", table_name="source_chunks")
    op.drop_index("ix_source_chunks_workspace_object", table_name="source_chunks")
    op.drop_index(
        "ix_source_chunks_workspace_status_version", table_name="source_chunks"
    )
    op.drop_table("source_chunks")
