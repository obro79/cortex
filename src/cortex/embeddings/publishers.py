from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import EmbeddingRecord
from cortex.contracts.pipeline_events import (
    PipelineEventEnvelope,
    PipelineHashes,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
    PipelineVersions,
)
from cortex.events.bus import EventBus


class EmbeddingPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_requested(self, record: EmbeddingRecord) -> PipelineEventEnvelope:
        envelope = self._envelope("embedding.requested", record)
        await self.event_bus.publish(envelope)
        return envelope

    async def publish_completed(self, record: EmbeddingRecord) -> PipelineEventEnvelope:
        envelope = self._envelope("embedding.completed", record)
        await self.event_bus.publish(envelope)
        return envelope

    def _envelope(
        self, event_type: str, record: EmbeddingRecord
    ) -> PipelineEventEnvelope:
        return PipelineEventEnvelope(
            event_id=f"evt_embedding_{uuid4().hex}",
            event_type=event_type,
            published_at=datetime.now(UTC),
            workspace_id=record.workspace_id,
            partition_key=f"{record.workspace_id}:{record.source_chunk_id}",
            subject=PipelineSubject(type="embedding_record", id=record.id),
            versions=PipelineVersions(
                embedding_version=record.embedding_version,
                chunking_version=record.chunking_version,
            ),
            hashes=PipelineHashes(
                text_hash=record.input_text_hash, vector_hash=record.vector_hash
            ),
            trace=PipelineTrace(trace_id=f"trace_{record.id}"),
            producer=PipelineProducer(service="embedding", instance_id="local"),
            payload={
                "provider": record.provider,
                "model": record.model,
                "dimensions": record.dimensions,
                "status": record.status,
            },
        )
