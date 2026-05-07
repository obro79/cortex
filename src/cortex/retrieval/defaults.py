from __future__ import annotations

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.vector_memory import InMemoryVectorIndex

from .publishers import EvidencePackPublisher
from .repositories import (
    InMemoryEvidencePackRepository,
    InMemoryRetrievalRequestRepository,
)
from .service import RetrievalService


def create_empty_retrieval_service() -> RetrievalService:
    event_bus = InMemoryEventBus()
    return RetrievalService(
        config=load_retrieval_config(),
        source_chunks=InMemorySourceChunkRepository(),
        vector_index=InMemoryVectorIndex(),
        request_repository=InMemoryRetrievalRequestRepository(),
        evidence_repository=InMemoryEvidencePackRepository(),
        publisher=EvidencePackPublisher(event_bus),
    )
