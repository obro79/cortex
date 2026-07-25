from __future__ import annotations

from cortex.canonical_memory.repositories import InMemoryCanonicalDecisionRepository
from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.context_gate.publishers import ContextGatePublisher
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.context_gate.service import ContextGateService
from cortex.contracts.entities import SourceChunk
from cortex.contracts.enums import SourceChunkStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.ingestion.payloads import sha256_digest

from .publishers import EvidencePackPublisher
from .repositories import (
    InMemoryEvidencePackRepository,
    InMemoryRetrievalRequestRepository,
)
from .service import RetrievalService


def create_empty_retrieval_service() -> RetrievalService:
    event_bus = InMemoryEventBus()
    source_chunks = InMemorySourceChunkRepository()
    _seed_default_source_chunk(source_chunks)
    return RetrievalService(
        config=load_retrieval_config(),
        source_chunks=source_chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(event_bus),
        canonical_decisions=InMemoryCanonicalDecisionRepository(),
    )


def create_empty_context_gate_service() -> ContextGateService:
    event_bus = InMemoryEventBus()
    source_chunks = InMemorySourceChunkRepository()
    _seed_default_source_chunk(source_chunks)
    retrieval_service = RetrievalService(
        config=load_retrieval_config(),
        source_chunks=source_chunks,
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(event_bus),
    )
    return ContextGateService(
        retrieval_service=retrieval_service,
        repository=InMemoryContextGateResultRepository(),
        publisher=ContextGatePublisher(event_bus),
    )


def _seed_default_source_chunk(repository: InMemorySourceChunkRepository) -> None:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    text = "Session migration storage uses Postgres as canonical guidance for COR-123."
    repository.upsert_many(
        [
            SourceChunk(
                id="chunk_default_session_guidance",
                workspace_id="ws_1",
                source_object_id="so_default_session_guidance",
                chunk_type="docs",
                chunk_index=0,
                text=text,
                text_hash=sha256_digest(text.encode()),
                token_count=len(text.split()),
                chunking_version="chunking-v1",
                citation_label="Default session guidance",
                citation_url=None,
                metadata_json={"source_kind": "repo_docs"},
                status=SourceChunkStatus.ACTIVE,
                created_from_hash=sha256_digest(text.encode()),
                created_at=now,
                updated_at=now,
            )
        ]
    )
