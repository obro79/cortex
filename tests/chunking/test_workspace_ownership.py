from cortex.chunking.config import load_retrieval_config
from cortex.chunking.publishers import SourceChunkPublisher
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.service import ChunkingService
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.events.in_memory import InMemoryEventBus
from cortex.normalization.publishers import SourceObjectPublisher
from cortex.normalization.repositories import (
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
)


async def test_chunking_service_ignores_cross_workspace_source_object_event(
    phase4_source_object: SourceObject,
) -> None:
    source_objects = InMemorySourceObjectRepository()
    source_objects.upsert_many([phase4_source_object])
    event_bus = InMemoryEventBus()
    service = ChunkingService(
        source_objects=source_objects,
        source_files=InMemorySourceFileRepository(),
        source_chunks=InMemorySourceChunkRepository(),
        chunker=SourceAwareChunker(load_retrieval_config().chunking),
        publisher=SourceChunkPublisher(event_bus),
    )
    source_event = await SourceObjectPublisher(event_bus).publish_upserted(
        phase4_source_object,
        raw_event_id="raw_1",
        payload_hash="sha256:payload",
        operation="inserted",
    )

    result = await service.handle_source_object_upserted(
        source_event.model_copy(update={"workspace_id": "ws_other"})
    )

    assert result.status == "ignored"
    assert result.reason == "workspace_mismatch"
    assert [event.event_type for event in event_bus.list_events()] == [
        "source_object.upserted"
    ]
