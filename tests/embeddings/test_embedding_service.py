import pytest

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.embeddings.publishers import EmbeddingPublisher
from cortex.embeddings.repositories import InMemoryEmbeddingRecordRepository
from cortex.embeddings.service import EmbeddingService
from cortex.events.in_memory import InMemoryEventBus
from cortex.platform import (
    InMemoryEphemeralCache,
    RateLimitExceededError,
    RateLimitPolicy,
    RateLimitService,
)


async def test_embedding_service_queues_completes_and_noops_same_chunk(
    phase4_source_object: SourceObject,
) -> None:
    source_chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    source_chunks.upsert_many([chunk])
    bus = InMemoryEventBus()
    service = EmbeddingService(
        source_chunks=source_chunks,
        embeddings=InMemoryEmbeddingRecordRepository(),
        provider=DeterministicEmbeddingProvider(dimensions=8, version="emb-v1"),
        publisher=EmbeddingPublisher(bus),
    )

    queued = await service.queue_for_chunk(chunk.id)
    noop = await service.queue_for_chunk(chunk.id)
    completed = await service.complete(queued.record.id)

    assert queued.operation == "inserted"
    assert queued.record.provider == "deterministic"
    assert queued.record.model == "fixture-vector-v1"
    assert queued.record.dimensions == 8
    assert noop.operation == "noop"
    assert completed.vector_hash is not None
    assert [event.event_type for event in bus.list_events()] == [
        "embedding.requested",
        "embedding.completed",
    ]


async def test_embedding_service_enforces_model_rate_limit(
    phase4_source_object: SourceObject,
) -> None:
    source_chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    source_chunks.upsert_many([chunk])
    bus = InMemoryEventBus()
    service = EmbeddingService(
        source_chunks=source_chunks,
        embeddings=InMemoryEmbeddingRecordRepository(),
        provider=DeterministicEmbeddingProvider(dimensions=8, version="emb-v1"),
        publisher=EmbeddingPublisher(bus),
        model_rate_limiter=RateLimitService(InMemoryEphemeralCache()),
        model_rate_limit_policy=RateLimitPolicy(
            name="embedding", limit=1, window_seconds=60, namespace="model"
        ),
    )

    first = await service.queue_for_chunk(chunk.id)
    completed = await service.complete(first.record.id)
    second = await service.queue_for_chunk(chunk.id)

    assert completed.vector_hash is not None
    with pytest.raises(RateLimitExceededError):
        await service.complete(second.record.id)


async def test_embedding_service_persists_composed_vector_collection(
    phase4_source_object: SourceObject,
) -> None:
    source_chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    source_chunks.upsert_many([chunk])
    service = EmbeddingService(
        source_chunks=source_chunks,
        embeddings=InMemoryEmbeddingRecordRepository(),
        provider=DeterministicEmbeddingProvider(dimensions=8, version="emb-v1"),
        publisher=EmbeddingPublisher(InMemoryEventBus()),
        vector_collection="cortex-test-fixture-vector-v1-emb-v1-8",
    )

    queued = await service.queue_for_chunk(chunk.id)
    completed = await service.complete(queued.record.id)

    assert completed.qdrant_collection == "cortex-test-fixture-vector-v1-emb-v1-8"
