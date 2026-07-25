from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.retrieval.publishers import EvidencePackPublisher
from cortex.retrieval.repositories import (
    InMemoryEvidencePackRepository,
    InMemoryRetrievalRequestRepository,
)
from cortex.retrieval.service import RetrievalService


async def test_retrieval_service_builds_evidence_pack_and_event(
    phase4_source_object,
) -> None:
    config = load_retrieval_config()
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(config.chunking).chunks_for_source_object(
        phase4_source_object
    )[0]
    chunks.upsert_many([chunk])
    bus = InMemoryEventBus()
    service = RetrievalService(
        config=config,
        source_chunks=chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(bus),
    )

    response = await service.retrieve_context(
        workspace_id="ws_1", query="session reads COR-123"
    )

    assert response.ok is True
    assert response.evidence_pack_id is not None
    assert response.status == "completed"
    assert "COR-123" in response.text
    assert "allow" not in response.evidence_pack
    assert bus.list_events()[0].event_type == "evidence_pack.created"


async def test_retrieval_service_applies_allowlist_before_evidence(
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
    )

    response = await service.retrieve_context(
        workspace_id="ws_1",
        query="session reads",
        source_allowlist=["not_so_1"],
    )

    assert response.evidence_pack["citations_json"] == {"items": []}
    assert response.evidence_pack["permission_exclusions_json"]["excluded_count"] == 0
