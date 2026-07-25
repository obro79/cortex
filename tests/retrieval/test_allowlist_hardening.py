from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.permissions.scopes import InMemoryPermissionScopeRepository
from cortex.permissions.service import PermissionService
from cortex.retrieval.publishers import EvidencePackPublisher
from cortex.retrieval.repositories import (
    InMemoryEvidencePackRepository,
    InMemoryRetrievalRequestRepository,
)
from cortex.retrieval.service import RetrievalService


async def test_retrieval_with_permission_service_fails_closed_without_scopes(
    phase4_source_object,
) -> None:
    config = load_retrieval_config()
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(config.chunking).chunks_for_source_object(
        phase4_source_object
    )[0]
    chunks.upsert_many([chunk])
    service = RetrievalService(
        config=config,
        source_chunks=chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(InMemoryEventBus()),
        permission_service=PermissionService(InMemoryPermissionScopeRepository()),
    )

    response = await service.retrieve_context(
        workspace_id="ws_1", query="session reads COR-123"
    )

    assert response.evidence_pack["citations_json"] == {"items": []}
    exclusions = response.evidence_pack["permission_exclusions_json"]
    assert exclusions["excluded_count"] > 0
    assert exclusions["reason"] == "no_active_permission_scope"


async def test_caller_source_filter_never_bypasses_permission_scopes(
    phase4_source_object,
) -> None:
    config = load_retrieval_config()
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(config.chunking).chunks_for_source_object(
        phase4_source_object
    )[0]
    chunks.upsert_many([chunk])
    service = RetrievalService(
        config=config,
        source_chunks=chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(InMemoryEventBus()),
        permission_service=PermissionService(InMemoryPermissionScopeRepository()),
    )

    response = await service.retrieve_context(
        workspace_id="ws_1",
        query="session reads COR-123",
        source_allowlist=[chunk.source_object_id],
    )

    assert response.evidence_pack["citations_json"] == {"items": []}
    assert (
        response.evidence_pack["permission_exclusions_json"]["reason"]
        == "no_active_permission_scope"
    )


async def test_retrieval_with_permission_service_allows_linear_team_scope(
    phase4_source_object,
) -> None:
    source_object = phase4_source_object.model_copy(
        update={
            "content_text": "COR-123 migrate session reads",
            "metadata_json": {"source_kind": "linear_task", "team_id": "team_1"},
        }
    )
    config = load_retrieval_config()
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(config.chunking).chunks_for_source_object(source_object)[
        0
    ]
    chunks.upsert_many([chunk])
    scopes = InMemoryPermissionScopeRepository()
    scopes.upsert_active(
        workspace_id="ws_1",
        provider="linear",
        scope_type="linear_team",
        external_id="team_1",
    )
    service = RetrievalService(
        config=config,
        source_chunks=chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(InMemoryEventBus()),
        permission_service=PermissionService(scopes),
    )

    response = await service.retrieve_context(
        workspace_id="ws_1", query="session reads COR-123"
    )

    assert response.ok is True
    assert "COR-123" in response.text
    assert response.evidence_pack["permission_exclusions_json"]["excluded_count"] == 0
