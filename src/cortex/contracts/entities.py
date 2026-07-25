"""Broad Phase 0 Pydantic entity stubs for v1 pipeline records."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from cortex.contracts.enums import (
    ApprovalStatus,
    ContextGateStatus,
    DeletionRequestStatus,
    EmbeddingJobStatus,
    EvidencePackStatus,
    IndexJobStatus,
    RawEventStatus,
    SourceChunkStatus,
    SourceObjectStatus,
)
from cortex.contracts.ids import JsonObject


class EntityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class RetryFields(EntityModel):
    attempt_count: int = Field(default=0, ge=0)
    last_error_code: str | None = None
    last_error_message: str | None = None
    next_retry_at: datetime | None = None
    last_attempt_at: datetime | None = None


class RawEvent(RetryFields):
    id: str
    workspace_id: str
    source_connection_id: str
    provider: str
    external_event_id: str
    event_type: str
    external_object_key: str | None = None
    idempotency_key: str
    payload_ref: str | None = None
    payload_hash: str | None = None
    payload_size_bytes: int | None = Field(default=None, ge=0)
    occurred_at: datetime | None = None
    received_at: datetime
    published_at: datetime | None = None
    processed_at: datetime | None = None
    status: RawEventStatus
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceObject(EntityModel):
    id: str
    workspace_id: str
    source_connection_id: str
    provider: str
    object_type: str
    external_object_id: str
    external_object_key: str
    parent_object_id: str | None = None
    title: str | None = None
    canonical_url: str | None = None
    author_external_id: str | None = None
    occurred_at: datetime | None = None
    source_updated_at: datetime | None = None
    normalized_version: str | None = None
    content_hash: str | None = None
    metadata_json: JsonObject = Field(default_factory=dict)
    status: SourceObjectStatus
    superseded_by_id: str | None = None
    deleted_at: datetime | None = None
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceFile(EntityModel):
    id: str
    workspace_id: str
    source_object_id: str | None = None
    source_connection_id: str | None = None
    provider: str | None = None
    external_file_id: str | None = None
    external_object_key: str | None = None
    file_name_hash: str | None = None
    content_type: str | None = None
    storage_ref: str | None = None
    content_hash: str | None = None
    ocr_text: str | None = None
    ocr_text_hash: str | None = None
    metadata_json: JsonObject = Field(default_factory=dict)
    status: SourceObjectStatus = SourceObjectStatus.ACTIVE
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class SourceChunk(EntityModel):
    id: str
    workspace_id: str
    source_object_id: str
    source_file_id: str | None = None
    chunk_type: str
    chunk_index: int = Field(ge=0)
    text: str
    text_hash: str
    token_count: int | None = Field(default=None, ge=0)
    chunking_version: str
    citation_label: str | None = None
    citation_url: str | None = None
    metadata_json: JsonObject = Field(default_factory=dict)
    status: SourceChunkStatus
    created_from_hash: str | None = None
    created_at: datetime
    updated_at: datetime


class EmbeddingRecord(RetryFields):
    id: str
    workspace_id: str
    source_chunk_id: str
    provider: str
    model: str
    dimensions: int = Field(gt=0)
    task_type: str | None = None
    embedding_version: str
    chunking_version: str
    input_text_hash: str
    vector_hash: str | None = None
    qdrant_collection: str | None = None
    qdrant_point_id: str | None = None
    status: EmbeddingJobStatus
    model_invocation_id: str | None = None
    created_at: datetime
    updated_at: datetime


class IndexJob(RetryFields):
    id: str
    workspace_id: str
    target_store: str
    target_type: str
    target_id: str
    operation: str
    index_version: str
    status: IndexJobStatus
    completed_at: datetime | None = None
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class RetrievalRequest(EntityModel):
    id: str
    workspace_id: str
    caller_type: str
    caller_id: str | None = None
    query: str
    task_hints_json: JsonObject = Field(default_factory=dict)
    filters_json: JsonObject = Field(default_factory=dict)
    source_allowlist_snapshot_hash: str | None = None
    status: str
    trace_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    created_at: datetime
    updated_at: datetime


class EvidencePack(EntityModel):
    id: str
    workspace_id: str
    retrieval_request_id: str
    status: EvidencePackStatus
    claims_json: JsonObject = Field(default_factory=dict)
    citations_json: JsonObject = Field(default_factory=dict)
    candidate_summary_json: JsonObject = Field(default_factory=dict)
    source_coverage_json: JsonObject = Field(default_factory=dict)
    permission_exclusions_json: JsonObject = Field(default_factory=dict)
    missing_context_json: JsonObject = Field(default_factory=dict)
    stale_context_json: JsonObject = Field(default_factory=dict)
    conflict_summary_json: JsonObject = Field(default_factory=dict)
    token_budget: int | None = Field(default=None, ge=0)
    ranker_version: str | None = None
    created_at: datetime
    consumed_at: datetime | None = None
    expires_at: datetime | None = None


class ContextGateResult(EntityModel):
    id: str
    workspace_id: str
    retrieval_request_id: str
    evidence_pack_id: str
    status: ContextGateStatus
    risk_category: str | None = None
    reasons_json: JsonObject = Field(default_factory=dict)
    required_actions_json: JsonObject = Field(default_factory=dict)
    gate_version: str
    evaluated_at: datetime
    resolved_at: datetime | None = None
    resolution_action: str | None = None
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CanonicalDecision(EntityModel):
    id: str
    workspace_id: str
    scope_type: str
    scope_ref: str
    title: str
    decision_text: str
    status: ApprovalStatus
    evidence_pack_id: str | None = None
    supersedes_decision_id: str | None = None
    superseded_by_decision_id: str | None = None
    created_by_actor_id: str | None = None
    approved_by_actor_id: str | None = None
    approved_at: datetime | None = None
    source_citations_json: JsonObject = Field(default_factory=dict)
    stale_or_superseded_evidence_json: JsonObject = Field(default_factory=dict)
    decision_version: str
    created_at: datetime
    updated_at: datetime


class ApprovalRecord(EntityModel):
    id: str
    workspace_id: str
    actor_id: str
    target_type: str
    target_id: str
    action: str
    original_text: str | None = None
    final_text: str | None = None
    rationale: str | None = None
    evidence_pack_id: str | None = None
    created_at: datetime
    trace_id: str | None = None


class DeletionRequest(RetryFields):
    id: str
    workspace_id: str
    requested_by_actor_id: str
    scope_type: str
    scope_ref: str
    reason: str | None = None
    status: DeletionRequestStatus
    affected_stores_json: JsonObject = Field(default_factory=dict)
    deleted_counts_json: JsonObject = Field(default_factory=dict)
    verification_result_json: JsonObject = Field(default_factory=dict)
    requested_at: datetime
    validated_at: datetime | None = None
    completed_at: datetime | None = None
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DeletionTombstone(EntityModel):
    id: str
    workspace_id: str
    deletion_request_id: str
    resource_type: str
    resource_hash: str
    provider: str | None = None
    external_object_key_hash: str | None = None
    deleted_at: datetime
    retention_expires_at: datetime | None = None
