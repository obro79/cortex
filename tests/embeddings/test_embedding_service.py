from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.embeddings.publishers import EmbeddingPublisher
from cortex.embeddings.repositories import InMemoryEmbeddingRecordRepository
from cortex.embeddings.service import EmbeddingService
from cortex.events.in_memory import InMemoryEventBus


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
    assert noop.operation == "noop"
    assert completed.vector_hash is not None
    assert [event.event_type for event in bus.list_events()] == [
        "embedding.requested",
        "embedding.completed",
    ]
