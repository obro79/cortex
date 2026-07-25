from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.embeddings.publishers import EmbeddingPublisher
from cortex.embeddings.repositories import InMemoryEmbeddingRecordRepository
from cortex.embeddings.service import EmbeddingService
from cortex.events.in_memory import InMemoryEventBus
from cortex.workers.embeddings import EmbeddingWorkerSkeleton


async def test_embedding_worker_queues_and_completes_source_chunk(
    phase4_source_object: SourceObject,
) -> None:
    source_chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    source_chunks.upsert_many([chunk])
    event_bus = InMemoryEventBus()
    service = EmbeddingService(
        source_chunks=source_chunks,
        embeddings=InMemoryEmbeddingRecordRepository(),
        provider=DeterministicEmbeddingProvider(dimensions=8, version="emb-v1"),
        publisher=EmbeddingPublisher(event_bus),
    )
    worker = EmbeddingWorkerSkeleton(service)

    chunk_event = await _publish_chunk_event(chunk, event_bus)
    queued = await worker.handle_source_chunk_upserted(chunk_event)
    requested_event = event_bus.list_events()[-1]
    completed = await worker.handle_embedding_requested(requested_event)

    assert queued["status"] == "queued"
    assert queued["operation"] == "inserted"
    assert completed["status"] == "completed"
    assert [event.event_type for event in event_bus.list_events()] == [
        "source_chunk.upserted",
        "embedding.requested",
        "embedding.completed",
    ]


async def _publish_chunk_event(chunk, event_bus: InMemoryEventBus):
    from cortex.chunking.publishers import SourceChunkPublisher

    return await SourceChunkPublisher(event_bus).publish_upserted(
        chunk,
        operation="inserted",
    )
