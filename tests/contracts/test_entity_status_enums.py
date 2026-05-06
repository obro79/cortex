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


def values(enum_type: type) -> list[str]:
    return [member.value for member in enum_type]


def test_raw_event_status_values_match_docs() -> None:
    assert values(RawEventStatus) == [
        "received",
        "persisted",
        "published",
        "processing",
        "processed",
        "failed_retryable",
        "deadlettered",
        "deleted",
    ]


def test_source_object_status_values_match_docs() -> None:
    assert values(SourceObjectStatus) == ["active", "superseded", "stale", "deleted"]


def test_source_chunk_status_values_match_docs() -> None:
    assert values(SourceChunkStatus) == ["active", "stale", "deleted"]


def test_embedding_job_status_values_match_docs() -> None:
    assert values(EmbeddingJobStatus) == [
        "queued",
        "processing",
        "provider_rate_limited",
        "scheduled_retry",
        "completed",
        "failed_retryable",
        "failed_terminal",
        "deadlettered",
        "stale",
    ]


def test_index_job_status_values_match_docs() -> None:
    assert values(IndexJobStatus) == [
        "queued",
        "processing",
        "completed",
        "failed_retryable",
        "failed_terminal",
        "deadlettered",
        "stale",
    ]


def test_evidence_pack_status_values_match_docs() -> None:
    assert values(EvidencePackStatus) == ["created", "consumed", "expired", "deleted"]


def test_context_gate_status_values_match_docs() -> None:
    assert values(ContextGateStatus) == ["allow", "warn", "block", "failed"]


def test_approval_status_values_match_docs() -> None:
    assert values(ApprovalStatus) == [
        "proposed",
        "needs_review",
        "approved",
        "edited",
        "rejected",
        "marked_unresolved",
        "superseded",
    ]


def test_deletion_request_status_values_match_docs() -> None:
    assert values(DeletionRequestStatus) == [
        "requested",
        "validated",
        "deleting",
        "verifying",
        "tombstoned",
        "completed",
        "failed_retryable",
        "failed_terminal",
        "manual_repair",
    ]
