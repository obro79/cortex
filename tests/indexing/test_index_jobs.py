from cortex.events.in_memory import InMemoryEventBus
from cortex.indexing.publishers import IndexPublisher
from cortex.indexing.repositories import InMemoryIndexJobRepository
from cortex.indexing.service import IndexJobService


async def test_index_job_service_idempotent_enqueue_and_complete_events() -> None:
    bus = InMemoryEventBus()
    service = IndexJobService(InMemoryIndexJobRepository(), IndexPublisher(bus))

    first = await service.enqueue_for_chunk(
        workspace_id="ws_1",
        source_chunk_id="chunk_1",
        target_store="postgres_fts",
        index_version="fts-v1",
    )
    second = await service.enqueue_for_chunk(
        workspace_id="ws_1",
        source_chunk_id="chunk_1",
        target_store="postgres_fts",
        index_version="fts-v1",
    )
    completed = await service.complete(first.record.id)

    assert first.operation == "inserted"
    assert second.operation == "noop"
    assert completed.completed_at is not None
    assert [event.event_type for event in bus.list_events()] == [
        "index.requested",
        "index.completed",
    ]
