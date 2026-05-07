from cortex.chunking.config import load_retrieval_config
from cortex.chunking.publishers import SourceChunkPublisher
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.events.in_memory import InMemoryEventBus


async def test_source_chunk_upserted_envelope_is_pointer_only(
    phase4_source_object: SourceObject,
) -> None:
    bus = InMemoryEventBus()
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(phase4_source_object)[0]

    envelope = await SourceChunkPublisher(bus).publish_upserted(
        chunk, source_object_event_id="evt_so_1", operation="inserted"
    )

    assert envelope.event_type == "source_chunk.upserted"
    assert envelope.subject.type == "source_chunk"
    assert envelope.versions.chunking_version == "chunking-v1"
    assert envelope.hashes.text_hash == chunk.text_hash
    assert envelope.payload == {
        "chunk_type": "linear_issue_overview",
        "operation": "inserted",
    }
    assert "text" not in envelope.payload
