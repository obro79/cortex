from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import SourceChunk
from cortex.contracts.pipeline_events import (
    PipelineCausation,
    PipelineEventEnvelope,
    PipelineHashes,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
    PipelineVersions,
)
from cortex.events.bus import EventBus


class SourceChunkPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_upserted(
        self,
        source_chunk: SourceChunk,
        *,
        source_object_event_id: str | None = None,
        operation: str,
    ) -> PipelineEventEnvelope:
        envelope = PipelineEventEnvelope(
            event_id=f"evt_chunk_{uuid4().hex}",
            event_type="source_chunk.upserted",
            published_at=datetime.now(UTC),
            workspace_id=source_chunk.workspace_id,
            partition_key=f"{source_chunk.workspace_id}:{source_chunk.source_object_id}",
            subject=PipelineSubject(type="source_chunk", id=source_chunk.id),
            causation=PipelineCausation(source_object_id=source_chunk.source_object_id),
            versions=PipelineVersions(chunking_version=source_chunk.chunking_version),
            hashes=PipelineHashes(text_hash=source_chunk.text_hash),
            trace=PipelineTrace(
                trace_id=f"trace_{source_chunk.id}",
                parent_event_id=source_object_event_id,
            ),
            producer=PipelineProducer(service="chunking", instance_id="local"),
            payload={"chunk_type": source_chunk.chunk_type, "operation": operation},
        )
        await self.event_bus.publish(envelope)
        return envelope
