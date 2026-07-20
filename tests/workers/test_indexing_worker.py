from cortex.chunking.config import load_retrieval_config
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.contracts.enums import IndexJobStatus, SourceChunkStatus
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.embeddings.publishers import EmbeddingPublisher
from cortex.embeddings.repositories import InMemoryEmbeddingRecordRepository
from cortex.embeddings.service import EmbeddingService
from cortex.events.in_memory import InMemoryEventBus
from cortex.events.retry import RetryPolicy
from cortex.indexing.publishers import IndexPublisher
from cortex.indexing.repositories import InMemoryIndexJobRepository
from cortex.indexing.service import IndexJobService
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.workers.indexing import IndexWorker


async def test_index_worker_delivers_completed_embedding_idempotently(
    phase4_source_object: SourceObject,
) -> None:
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    chunk = chunk.model_copy(
        update={"metadata_json": {**chunk.metadata_json, "provider": "linear"}}
    )
    chunks.upsert_many([chunk])
    event_bus = InMemoryEventBus()
    embeddings = InMemoryEmbeddingRecordRepository()
    provider = DeterministicEmbeddingProvider(dimensions=8, version="emb-v1")
    embedding_service = EmbeddingService(
        source_chunks=chunks,
        embeddings=embeddings,
        provider=provider,
        publisher=EmbeddingPublisher(event_bus),
    )
    queued = await embedding_service.queue_for_chunk(chunk.id)
    await embedding_service.complete(queued.record.id)
    index_jobs = InMemoryIndexJobRepository()
    vector_index = InMemoryVectorIndex()
    index_service = IndexJobService(index_jobs, IndexPublisher(event_bus))
    worker = IndexWorker(
        index_service=index_service,
        embeddings=embeddings,
        source_chunks=chunks,
        embedding_provider=provider,
        vector_index=vector_index,
    )

    indexed = await worker.handle_embedding_completed(event_bus.list_events()[-1])
    requested = event_bus.list_events()[-1]
    delivered = await worker.handle_index_requested(requested)
    duplicate = await worker.handle_index_requested(requested)

    assert indexed["status"] == "queued"
    assert indexed["operation"] == "inserted"
    assert delivered["status"] == "completed"
    assert duplicate == {
        "status": "completed",
        "index_job_id": indexed["index_job_id"],
        "operation": "noop",
    }
    embedding = embeddings.get_by_id(queued.record.id)
    point = vector_index.points["fixture-cortex-dev"][embedding.id]
    assert point[1] == {
        "workspace_id": chunk.workspace_id,
        "source_object_id": chunk.source_object_id,
        "source_chunk_id": chunk.id,
        "chunk_type": chunk.chunk_type,
        "chunking_version": chunk.chunking_version,
        "content_hash": chunk.text_hash,
        "embedding_id": embedding.id,
        "embedding_model": embedding.model,
        "embedding_version": embedding.embedding_version,
        "status": "active",
        "provider": "linear",
        "source_type": "linear_issue",
    }
    assert [event.event_type for event in event_bus.list_events()] == [
        "embedding.requested",
        "embedding.completed",
        "index.requested",
        "index.completed",
    ]

    delete = await index_service.enqueue_for_embedding(embedding, operation="delete")
    deleted = await worker.handle_index_requested(event_bus.list_events()[-1])
    rebuild = await index_service.enqueue_for_embedding(embedding, operation="rebuild")
    rebuilt = await worker.handle_index_requested(event_bus.list_events()[-1])

    assert delete.operation == "inserted"
    assert deleted["status"] == "completed"
    assert rebuild.operation == "inserted"
    assert rebuilt["status"] == "completed"
    assert embedding.id in vector_index.points["fixture-cortex-dev"]


async def test_index_worker_records_retryable_unready_vector_delivery(
    phase4_source_object: SourceObject,
) -> None:
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    chunks.upsert_many([chunk])
    event_bus = InMemoryEventBus()
    embeddings = InMemoryEmbeddingRecordRepository()
    provider = DeterministicEmbeddingProvider(dimensions=8, version="emb-v1")
    embedding_service = EmbeddingService(
        source_chunks=chunks,
        embeddings=embeddings,
        provider=provider,
        publisher=EmbeddingPublisher(event_bus),
    )
    queued = await embedding_service.queue_for_chunk(chunk.id)
    await embedding_service.complete(queued.record.id)
    index_jobs = InMemoryIndexJobRepository()
    worker = IndexWorker(
        index_service=IndexJobService(index_jobs, IndexPublisher(event_bus)),
        embeddings=embeddings,
        source_chunks=chunks,
        embedding_provider=provider,
        vector_index=None,
    )

    enqueued = await worker.handle_embedding_completed(event_bus.list_events()[-1])
    failed = await worker.handle_index_requested(event_bus.list_events()[-1])
    job = index_jobs.get_by_id(enqueued["index_job_id"])

    assert failed == {
        "status": "retryable",
        "index_job_id": job.id,
        "reason": "vector_index_unconfigured",
    }
    assert job.status == IndexJobStatus.FAILED_RETRYABLE
    assert job.attempt_count == 1
    assert job.last_error_code == "vector_index_unconfigured"
    assert job.next_retry_at is not None


async def test_index_worker_deletes_stale_chunk_instead_of_resurrecting_it(
    phase4_source_object: SourceObject,
) -> None:
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    chunks.upsert_many([chunk])
    events = InMemoryEventBus()
    embeddings = InMemoryEmbeddingRecordRepository()
    provider = DeterministicEmbeddingProvider(dimensions=8, version="emb-v1")
    embedding_service = EmbeddingService(
        source_chunks=chunks,
        embeddings=embeddings,
        provider=provider,
        publisher=EmbeddingPublisher(events),
    )
    queued = await embedding_service.queue_for_chunk(chunk.id)
    embedding = await embedding_service.complete(queued.record.id)
    chunks._records[chunk.id] = chunk.model_copy(  # noqa: SLF001 - fixture setup
        update={"status": SourceChunkStatus.STALE}
    )
    jobs = InMemoryIndexJobRepository()
    vectors = InMemoryVectorIndex()
    worker = IndexWorker(
        index_service=IndexJobService(jobs, IndexPublisher(events)),
        embeddings=embeddings,
        source_chunks=chunks,
        embedding_provider=provider,
        vector_index=vectors,
    )
    await worker.handle_embedding_completed(events.list_events()[-1])
    result = await worker.handle_index_requested(events.list_events()[-1])

    assert result["status"] == "completed"
    assert embedding.id not in vectors.points.get("fixture-cortex-dev", {})


async def test_index_worker_marks_invalid_job_terminal(
    phase4_source_object: SourceObject,
) -> None:
    chunks = InMemorySourceChunkRepository()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]
    chunks.upsert_many([chunk])
    events = InMemoryEventBus()
    embeddings = InMemoryEmbeddingRecordRepository()
    provider = DeterministicEmbeddingProvider(dimensions=8, version="emb-v1")
    embedding_service = EmbeddingService(
        source_chunks=chunks, embeddings=embeddings, provider=provider,
        publisher=EmbeddingPublisher(events),
    )
    queued = await embedding_service.queue_for_chunk(chunk.id)
    await embedding_service.complete(queued.record.id)
    jobs = InMemoryIndexJobRepository()
    worker = IndexWorker(
        index_service=IndexJobService(jobs, IndexPublisher(events)),
        embeddings=embeddings, source_chunks=chunks, embedding_provider=provider,
        vector_index=InMemoryVectorIndex(), retry_policy=RetryPolicy(max_attempts=1),
    )
    enqueued = await worker.handle_embedding_completed(events.list_events()[-1])
    job = jobs.get_by_id(enqueued["index_job_id"])
    jobs._records[job.id] = job.model_copy(update={"operation": "bad"})  # noqa: SLF001
    result = await worker.handle_index_requested(events.list_events()[-1])

    assert result["status"] == "terminal"
    assert jobs.get_by_id(job.id).status == IndexJobStatus.FAILED_TERMINAL
