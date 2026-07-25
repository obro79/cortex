from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
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


class OrganizationRecord(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        Index("ix_organizations_status", "status"),
        Index("ix_organizations_created_by", "created_by_user_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_workspaces_org_slug"),
        Index("ix_workspaces_organization_status", "organization_id", "status"),
        Index("ix_workspaces_created_by", "created_by_user_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserRecord(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "auth_provider", "auth_subject", name="uq_users_auth_provider_subject"
        ),
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    auth_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_subject: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MembershipRecord(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "workspace_id",
            "user_id",
            name="uq_memberships_scope_user",
        ),
        Index("ix_memberships_user_status", "user_id", "status"),
        Index("ix_memberships_workspace_role", "workspace_id", "role"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_by_user_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class InvitationRecord(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
        Index("ix_invitations_workspace_status", "workspace_id", "status"),
        Index("ix_invitations_email_status", "email", "status"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    invited_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    accepted_by_user_id: Mapped[str | None] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LegalConsentRecord(Base):
    __tablename__ = "legal_consents"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "consent_type", "version", name="uq_legal_consents_user_version"
        ),
        Index("ix_legal_consents_workspace_user", "workspace_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(String(128))
    workspace_id: Mapped[str | None] = mapped_column(String(128))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(128), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
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
    content_text: Mapped[str | None] = mapped_column(Text)
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


class DemoRunReportRecord(Base):
    """Append-only application projection for a controlled live run.

    The canonical ingestion/retrieval tables intentionally retain operational
    material that must never be serialized into a demo surface. This table is
    the small durable boundary between a trusted run finalizer and the
    read-only control plane: it stores internal source linkage plus a
    pre-validated public report, never source content, provider identifiers,
    query text, evidence JSON, or credentials. The application never exposes
    an update path; production deployment should further restrict the writer
    database role to insert/select for this table.
    """

    __tablename__ = "demo_run_reports"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "run_id_hash",
            name="uq_demo_run_reports_workspace_run",
        ),
        Index(
            "ix_demo_run_reports_workspace_completed",
            "workspace_id",
            "completed_at",
        ),
        Index(
            "ix_demo_run_reports_workspace_source_completed",
            "workspace_id",
            "source_connection_id",
            "completed_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # This is Cortex's internal source-connection ID, not a provider resource
    # identifier. The public projection exposes only source_ref_hash.
    source_connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    source_ref_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    collection: Mapped[str] = mapped_column(String(160), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    report_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RetrievalRequestRecord(Base):
    __tablename__ = "retrieval_requests"
    __table_args__ = (
        Index("ix_retrieval_requests_workspace_status", "workspace_id", "status"),
        Index("ix_retrieval_requests_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    caller_type: Mapped[str] = mapped_column(String(64), nullable=False)
    caller_id: Mapped[str | None] = mapped_column(String(128))
    query: Mapped[str] = mapped_column(String, nullable=False)
    task_hints_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    source_allowlist_snapshot_hash: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EvidencePackRecord(Base):
    __tablename__ = "evidence_packs"
    __table_args__ = (
        Index("ix_evidence_packs_workspace_status", "workspace_id", "status"),
        Index(
            "ix_evidence_packs_workspace_request",
            "workspace_id",
            "retrieval_request_id",
        ),
        Index("ix_evidence_packs_workspace_expires", "workspace_id", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    claims_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    citations_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    candidate_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    source_coverage_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    permission_exclusions_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    missing_context_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    stale_context_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    conflict_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    token_budget: Mapped[int | None] = mapped_column(Integer)
    ranker_version: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContextGateResultRecord(Base):
    __tablename__ = "context_gate_results"
    __table_args__ = (
        Index(
            "ix_context_gate_results_workspace_status_evaluated",
            "workspace_id",
            "status",
            "evaluated_at",
        ),
        Index(
            "ix_context_gate_results_workspace_risk_evaluated",
            "workspace_id",
            "risk_category",
            "evaluated_at",
        ),
        Index(
            "ix_context_gate_results_workspace_request",
            "workspace_id",
            "retrieval_request_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_pack_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_category: Mapped[str | None] = mapped_column(String(128))
    reasons_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    required_actions_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    gate_version: Mapped[str] = mapped_column(String(128), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_action: Mapped[str | None] = mapped_column(String(128))
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


class RetentionPolicyRecord(Base):
    __tablename__ = "retention_policies"
    __table_args__ = (Index("ix_retention_policies_workspace", "workspace_id"),)

    workspace_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    raw_event_days: Mapped[int | None] = mapped_column(Integer)
    payload_days: Mapped[int | None] = mapped_column(Integer)
    audit_log_days: Mapped[int | None] = mapped_column(Integer)
    tombstone_days: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DeletionTombstoneRecord(Base):
    __tablename__ = "deletion_tombstones"
    __table_args__ = (
        Index(
            "ix_deletion_tombstones_workspace_status",
            "workspace_id",
            "status",
        ),
        Index(
            "ix_deletion_tombstones_workspace_target",
            "workspace_id",
            "target_type",
            "target_id_hash",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExportJobRecord(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_workspace_status", "workspace_id", "status"),
        Index("ix_export_jobs_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    export_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    destination_ref: Mapped[str | None] = mapped_column(String(512))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BillingCustomerRecord(Base):
    __tablename__ = "billing_customers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "provider",
            name="uq_billing_customers_organization_provider",
        ),
        UniqueConstraint(
            "provider",
            "provider_customer_id",
            name="uq_billing_customers_provider_customer",
        ),
        Index("ix_billing_customers_organization_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_customer_id: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BillingSubscriptionRecord(Base):
    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_subscription_id",
            name="uq_billing_subscriptions_provider_subscription",
        ),
        Index(
            "ix_billing_subscriptions_organization_status",
            "organization_id",
            "status",
        ),
        Index(
            "ix_billing_subscriptions_customer",
            "billing_customer_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    billing_customer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(256))
    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    provider_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BillingUsageMeterRecord(Base):
    __tablename__ = "billing_usage_meters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "dimension",
            "period_key",
            name="uq_billing_usage_meters_period",
        ),
        Index(
            "ix_billing_usage_meters_organization_dimension",
            "organization_id",
            "dimension",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    period_key: Mapped[str] = mapped_column(String(128), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BillingUsageEventRecord(Base):
    __tablename__ = "billing_usage_events"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_billing_usage_events_idempotency",
        ),
        Index(
            "ix_billing_usage_events_organization_dimension",
            "organization_id",
            "dimension",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(256))
    period_key: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BillingWebhookEventRecord(Base):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_billing_webhook_events_provider_event",
        ),
        Index("ix_billing_webhook_events_status", "provider", "status"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_type: Mapped[str] = mapped_column(String(256), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(256))
    signature_status: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    api_version: Mapped[str | None] = mapped_column(String(64))
    livemode: Mapped[str | None] = mapped_column(String(16))
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )


class ProviderAclSnapshotRecord(Base):
    __tablename__ = "provider_acl_snapshots"
    __table_args__ = (
        Index(
            "ix_provider_acl_snapshots_current",
            "workspace_id",
            "provider",
            "resource_type",
            "resource_id_hash",
            "is_current",
        ),
        # A resource can have many historical snapshots but exactly one
        # authoritative current snapshot. The partial unique index closes the
        # update-then-insert race in ACL refreshes without preventing history.
        Index(
            "uq_provider_acl_snapshots_current_resource",
            "workspace_id",
            "provider",
            "resource_type",
            "resource_id_hash",
            unique=True,
            postgresql_where=text("is_current"),
            sqlite_where=text("is_current = 1"),
        ),
        Index("ix_provider_acl_snapshots_expires", "workspace_id", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    source_connection_id: Mapped[str | None] = mapped_column(String(128))
    snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_current: Mapped[bool] = mapped_column(nullable=False, default=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderAclEntryRecord(Base):
    __tablename__ = "provider_acl_entries"
    __table_args__ = (
        Index("ix_provider_acl_entries_snapshot", "snapshot_id"),
        Index(
            "ix_provider_acl_entries_principal",
            "workspace_id",
            "provider",
            "principal_type",
            "principal_id_hash",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(128), nullable=False)
    principal_id_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    permission: Mapped[str] = mapped_column(String(64), nullable=False)
    effect: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderPrincipalMappingRecord(Base):
    __tablename__ = "provider_principal_mappings"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            "provider",
            "principal_type",
            "principal_id_hash",
            name="uq_provider_principal_mapping",
        ),
        Index(
            "ix_provider_principal_mappings_user",
            "workspace_id",
            "user_id",
            "status",
            "expires_at",
        ),
        Index(
            "ix_provider_principal_mappings_principal",
            "workspace_id",
            "provider",
            "principal_type",
            "principal_id_hash",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(128), nullable=False)
    principal_id_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    match_method: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PermissionScopeRecord(Base):
    """Durable, hashed source-selection scope used by retrieval authorization."""

    __tablename__ = "permission_scopes"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "scope_type",
            "external_id_hash",
            name="uq_permission_scopes_identity",
        ),
        Index(
            "ix_permission_scopes_workspace_status",
            "workspace_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(128), nullable=False)
    external_id_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_by_actor_id: Mapped[str | None] = mapped_column(String(128))
    removed_by_actor_id: Mapped[str | None] = mapped_column(String(128))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CanonicalDecisionRecord(Base):
    __tablename__ = "canonical_decisions"
    __table_args__ = (
        Index(
            "ix_canonical_decisions_workspace_scope_status",
            "workspace_id",
            "scope_type",
            "scope_ref",
            "status",
        ),
        Index(
            "ix_canonical_decisions_workspace_status_approved",
            "workspace_id",
            "status",
            "approved_at",
        ),
        Index(
            "ix_canonical_decisions_workspace_supersedes",
            "workspace_id",
            "supersedes_decision_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    decision_text: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_pack_id: Mapped[str | None] = mapped_column(String(128))
    supersedes_decision_id: Mapped[str | None] = mapped_column(String(128))
    superseded_by_decision_id: Mapped[str | None] = mapped_column(String(128))
    created_by_actor_id: Mapped[str | None] = mapped_column(String(128))
    approved_by_actor_id: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_citations_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    stale_or_superseded_evidence_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    decision_version: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ApprovalRecordRecord(Base):
    __tablename__ = "approval_records"
    __table_args__ = (
        Index(
            "ix_approval_records_workspace_target",
            "workspace_id",
            "target_type",
            "target_id",
        ),
        Index(
            "ix_approval_records_workspace_actor_created",
            "workspace_id",
            "actor_id",
            "created_at",
        ),
        Index(
            "ix_approval_records_workspace_action_created",
            "workspace_id",
            "action",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    original_text: Mapped[str | None] = mapped_column(String)
    final_text: Mapped[str | None] = mapped_column(String)
    rationale: Mapped[str | None] = mapped_column(String)
    evidence_pack_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str | None] = mapped_column(String(128))


class SecretRefRecord(Base):
    __tablename__ = "secret_refs"
    __table_args__ = (
        Index("ix_secret_refs_workspace_provider", "workspace_id", "provider"),
        Index("ix_secret_refs_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    external_secret_id: Mapped[str] = mapped_column(String(512), nullable=False)
    key_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SecretMaterialRecord(Base):
    __tablename__ = "secret_materials"
    __table_args__ = (
        UniqueConstraint("secret_ref_id", name="uq_secret_materials_secret_ref"),
        Index("ix_secret_materials_workspace_provider", "workspace_id", "provider"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    secret_ref_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    encryption_scheme: Mapped[str] = mapped_column(String(128), nullable=False)
    key_version: Mapped[str] = mapped_column(String(128), nullable=False)
    ciphertext: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OAuthInstallationRecord(Base):
    __tablename__ = "oauth_installations"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "provider_workspace_id",
            name="uq_oauth_installations_provider_workspace",
        ),
        Index("ix_oauth_installations_workspace_status", "workspace_id", "status"),
        Index(
            "ix_oauth_installations_workspace_provider",
            "workspace_id",
            "provider",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    enterprise_id: Mapped[str | None] = mapped_column(String(128))
    bot_user_id: Mapped[str | None] = mapped_column(String(128))
    installing_actor_id: Mapped[str | None] = mapped_column(String(128))
    secret_ref_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    provider_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    health_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SourceConnectionRecord(Base):
    __tablename__ = "source_connections"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "external_source_id",
            name="uq_source_connections_provider_source",
        ),
        Index(
            "ix_source_connections_workspace_status",
            "workspace_id",
            "status",
        ),
        Index(
            "ix_source_connections_workspace_install",
            "workspace_id",
            "oauth_installation_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    oauth_installation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name_hash: Mapped[str | None] = mapped_column(String(128))
    selected: Mapped[bool] = mapped_column(nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WebhookDeliveryRecord(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "delivery_id",
            name="uq_webhook_deliveries_provider_delivery",
        ),
        Index("ix_webhook_deliveries_workspace_status", "workspace_id", "status"),
        Index("ix_webhook_deliveries_workspace_event", "workspace_id", "event_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(256))
    signature_status: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    source_connection_id: Mapped[str | None] = mapped_column(String(128))
    raw_event_id: Mapped[str | None] = mapped_column(String(128))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    trace_id: Mapped[str | None] = mapped_column(String(128))


class BackfillJobRecord(Base):
    __tablename__ = "backfill_jobs"
    __table_args__ = (
        Index("ix_backfill_jobs_workspace_status", "workspace_id", "status"),
        Index(
            "ix_backfill_jobs_workspace_source",
            "workspace_id",
            "source_connection_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    cursor_id: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ProviderCursorRecord(Base):
    __tablename__ = "provider_cursors"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "source_connection_id",
            "cursor_type",
            name="uq_provider_cursors_identity",
        ),
        Index("ix_provider_cursors_workspace_status", "workspace_id", "status"),
        Index(
            "ix_provider_cursors_workspace_source",
            "workspace_id",
            "source_connection_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cursor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    cursor_value: Mapped[str | None] = mapped_column(String(256))
    high_watermark: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    last_advanced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SchedulerLeaseRecord(Base):
    __tablename__ = "scheduler_leases"

    job_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fencing_token: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
