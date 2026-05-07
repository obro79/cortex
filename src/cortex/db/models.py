from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from cortex.db.base import Base


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RawEventRecord(Base):
    __tablename__ = "raw_events"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "external_event_id",
            name="uq_raw_events_provider_external_event",
        ),
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_raw_events_idempotency_key",
        ),
        Index(
            "ix_raw_events_workspace_source_received",
            "workspace_id",
            "source_connection_id",
            "received_at",
        ),
        Index(
            "ix_raw_events_workspace_status_retry",
            "workspace_id",
            "status",
            "next_retry_at",
        ),
        Index(
            "ix_raw_events_workspace_external_object",
            "workspace_id",
            "external_object_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_type: Mapped[str] = mapped_column(String(256), nullable=False)
    external_object_key: Mapped[str | None] = mapped_column(String(512))
    idempotency_key: Mapped[str] = mapped_column(String(512), nullable=False)
    payload_ref: Mapped[str | None] = mapped_column(String(512))
    payload_hash: Mapped[str | None] = mapped_column(String(128))
    payload_size_bytes: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    last_error_message: Mapped[str | None] = mapped_column(String(1024))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SourceObjectRecord(Base):
    __tablename__ = "source_objects"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "object_type",
            "external_object_id",
            name="uq_source_objects_external_identity",
        ),
        Index(
            "ix_source_objects_workspace_external_key",
            "workspace_id",
            "external_object_key",
        ),
        Index(
            "ix_source_objects_workspace_type_updated",
            "workspace_id",
            "object_type",
            "source_updated_at",
        ),
        Index("ix_source_objects_workspace_status", "workspace_id", "status"),
        Index(
            "ix_source_objects_workspace_content_hash", "workspace_id", "content_hash"
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(128), nullable=False)
    external_object_id: Mapped[str] = mapped_column(String(256), nullable=False)
    external_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    parent_object_id: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(String(512))
    canonical_url: Mapped[str | None] = mapped_column(String(1024))
    author_external_id: Mapped[str | None] = mapped_column(String(256))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalized_version: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    superseded_by_id: Mapped[str | None] = mapped_column(String(128))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SourceFileRecord(Base):
    __tablename__ = "source_files"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "external_file_id",
            name="uq_source_files_external_file",
        ),
        Index("ix_source_files_workspace_object", "workspace_id", "source_object_id"),
        Index(
            "ix_source_files_workspace_external_key",
            "workspace_id",
            "external_object_key",
        ),
        Index("ix_source_files_workspace_status", "workspace_id", "status"),
        Index("ix_source_files_workspace_content_hash", "workspace_id", "content_hash"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_object_id: Mapped[str | None] = mapped_column(String(128))
    source_connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    external_file_id: Mapped[str] = mapped_column(String(256), nullable=False)
    external_object_key: Mapped[str | None] = mapped_column(String(512))
    file_name_hash: Mapped[str | None] = mapped_column(String(128))
    content_type: Mapped[str | None] = mapped_column(String(128))
    storage_ref: Mapped[str | None] = mapped_column(String(512))
    content_hash: Mapped[str | None] = mapped_column(String(128))
    ocr_text: Mapped[str | None] = mapped_column(String)
    ocr_text_hash: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RelationshipSeedRecord(Base):
    __tablename__ = "relationship_seeds"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "relationship_type",
            "from_id",
            "to_id",
            "normalized_version",
            name="uq_relationship_seeds_identity",
        ),
        Index("ix_relationship_seeds_workspace_from", "workspace_id", "from_id"),
        Index("ix_relationship_seeds_workspace_to", "workspace_id", "to_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(128), nullable=False)
    from_id: Mapped[str] = mapped_column(String(128), nullable=False)
    to_id: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    raw_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_version: Mapped[str] = mapped_column(String(128), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SourceChunkRecord(Base):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source_object_id",
            "source_file_id",
            "chunk_type",
            "chunk_index",
            "chunking_version",
            name="uq_source_chunks_identity",
        ),
        Index(
            "ix_source_chunks_workspace_status_version",
            "workspace_id",
            "status",
            "chunking_version",
        ),
        Index("ix_source_chunks_workspace_object", "workspace_id", "source_object_id"),
        Index("ix_source_chunks_workspace_file", "workspace_id", "source_file_id"),
        Index("ix_source_chunks_workspace_text_hash", "workspace_id", "text_hash"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_object_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(String(128))
    chunk_type: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    chunking_version: Mapped[str] = mapped_column(String(128), nullable=False)
    citation_label: Mapped[str | None] = mapped_column(String(512))
    citation_url: Mapped[str | None] = mapped_column(String(1024))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_from_hash: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EmbeddingRecordRecord(Base):
    __tablename__ = "embedding_records"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source_chunk_id",
            "embedding_version",
            name="uq_embedding_records_chunk_version",
        ),
        Index("ix_embedding_records_workspace_status", "workspace_id", "status"),
        Index(
            "ix_embedding_records_workspace_chunk", "workspace_id", "source_chunk_id"
        ),
        Index(
            "ix_embedding_records_workspace_input_hash",
            "workspace_id",
            "input_text_hash",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[str | None] = mapped_column(String(128))
    embedding_version: Mapped[str] = mapped_column(String(128), nullable=False)
    chunking_version: Mapped[str] = mapped_column(String(128), nullable=False)
    input_text_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    vector_hash: Mapped[str | None] = mapped_column(String(128))
    qdrant_collection: Mapped[str | None] = mapped_column(String(128))
    qdrant_point_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    model_invocation_id: Mapped[str | None] = mapped_column(String(128))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    last_error_message: Mapped[str | None] = mapped_column(String(1024))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IndexJobRecord(Base):
    __tablename__ = "index_jobs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "target_store",
            "target_type",
            "target_id",
            "operation",
            "index_version",
            name="uq_index_jobs_identity",
        ),
        Index("ix_index_jobs_workspace_status", "workspace_id", "status"),
        Index(
            "ix_index_jobs_workspace_target", "workspace_id", "target_type", "target_id"
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_store: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    index_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str | None] = mapped_column(String(128))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    last_error_message: Mapped[str | None] = mapped_column(String(1024))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
