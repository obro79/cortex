from datetime import UTC, datetime

import pytest

from cortex.contracts.entities import (
    ApprovalRecord,
    CanonicalDecision,
    ContextGateResult,
    DeletionRequest,
    DeletionTombstone,
    EmbeddingRecord,
    EvidencePack,
    IndexJob,
    RawEvent,
    RetrievalRequest,
    SourceChunk,
    SourceFile,
    SourceObject,
)

NOW = datetime(2026, 5, 6, 18, 12, tzinfo=UTC)


def test_raw_event_serializes_stable_phase_zero_fields() -> None:
    raw_event = RawEvent(
        id="raw_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider="fixture",
        external_event_id="external_1",
        event_type="fixture.created",
        idempotency_key="idem_1",
        payload_hash="sha256:payload",
        received_at=NOW,
        status="received",
        created_at=NOW,
        updated_at=NOW,
    )

    assert raw_event.model_dump(mode="json")["status"] == "received"
    assert raw_event.model_dump(mode="json")["payload_hash"] == "sha256:payload"


@pytest.mark.parametrize(
    ("model_type", "payload", "status_field", "status_value"),
    [
        (
            SourceObject,
            {
                "id": "so_1",
                "workspace_id": "ws_1",
                "source_connection_id": "src_1",
                "provider": "fixture",
                "object_type": "fixture_doc",
                "external_object_id": "doc_1",
                "external_object_key": "fixture:doc_1",
                "status": "active",
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "active",
        ),
        (
            SourceFile,
            {
                "id": "file_1",
                "workspace_id": "ws_1",
                "source_object_id": "so_1",
                "content_hash": "sha256:file",
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "active",
        ),
        (
            SourceChunk,
            {
                "id": "chunk_1",
                "workspace_id": "ws_1",
                "source_object_id": "so_1",
                "chunk_type": "doc_section",
                "chunk_index": 0,
                "text": "fixture text",
                "text_hash": "sha256:text",
                "chunking_version": "fixture-chunker-v1",
                "status": "active",
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "active",
        ),
        (
            EmbeddingRecord,
            {
                "id": "emb_1",
                "workspace_id": "ws_1",
                "source_chunk_id": "chunk_1",
                "provider": "fixture",
                "model": "fixture-embedding",
                "dimensions": 3,
                "embedding_version": "fixture-embedding-v1",
                "chunking_version": "fixture-chunker-v1",
                "input_text_hash": "sha256:text",
                "status": "queued",
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "queued",
        ),
        (
            IndexJob,
            {
                "id": "idx_1",
                "workspace_id": "ws_1",
                "target_store": "postgres_fts",
                "target_type": "source_chunk",
                "target_id": "chunk_1",
                "operation": "upsert",
                "index_version": "fts-v1",
                "status": "queued",
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "queued",
        ),
        (
            RetrievalRequest,
            {
                "id": "ret_1",
                "workspace_id": "ws_1",
                "caller_type": "eval",
                "query": "What changed?",
                "status": "received",
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "received",
        ),
        (
            EvidencePack,
            {
                "id": "pack_1",
                "workspace_id": "ws_1",
                "retrieval_request_id": "ret_1",
                "status": "created",
                "created_at": NOW,
            },
            "status",
            "created",
        ),
        (
            ContextGateResult,
            {
                "id": "gate_1",
                "workspace_id": "ws_1",
                "retrieval_request_id": "ret_1",
                "evidence_pack_id": "pack_1",
                "status": "allow",
                "gate_version": "gate-v1",
                "evaluated_at": NOW,
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "allow",
        ),
        (
            CanonicalDecision,
            {
                "id": "decision_1",
                "workspace_id": "ws_1",
                "scope_type": "workspace",
                "scope_ref": "ws_1",
                "title": "Decision",
                "decision_text": "Use the fixture.",
                "status": "approved",
                "decision_version": "decision-v1",
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "approved",
        ),
        (
            ApprovalRecord,
            {
                "id": "approval_1",
                "workspace_id": "ws_1",
                "actor_id": "actor_1",
                "target_type": "canonical_decision",
                "target_id": "decision_1",
                "action": "approve",
                "created_at": NOW,
            },
            "action",
            "approve",
        ),
        (
            DeletionRequest,
            {
                "id": "del_1",
                "workspace_id": "ws_1",
                "requested_by_actor_id": "actor_1",
                "scope_type": "source_object",
                "scope_ref": "so_1",
                "status": "requested",
                "requested_at": NOW,
                "created_at": NOW,
                "updated_at": NOW,
            },
            "status",
            "requested",
        ),
        (
            DeletionTombstone,
            {
                "id": "tomb_1",
                "workspace_id": "ws_1",
                "deletion_request_id": "del_1",
                "resource_type": "source_object",
                "resource_hash": "sha256:resource",
                "deleted_at": NOW,
            },
            "resource_hash",
            "sha256:resource",
        ),
    ],
)
def test_entity_stubs_serialize_representative_objects(
    model_type: type,
    payload: dict,
    status_field: str,
    status_value: str,
) -> None:
    entity = model_type.model_validate(payload)

    dumped = entity.model_dump(mode="json")
    assert dumped[status_field] == status_value
    assert dumped["workspace_id"] == "ws_1"
