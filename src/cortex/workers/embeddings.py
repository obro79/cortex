from __future__ import annotations

from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.embeddings.service import EmbeddingService


class EmbeddingWorkerSkeleton:
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service

    async def handle_source_chunk_upserted(
        self, envelope: PipelineEventEnvelope
    ) -> dict[str, str]:
        if envelope.event_type != "source_chunk.upserted":
            return {"status": "ignored", "reason": "unsupported_event_type"}
        if envelope.subject.type != "source_chunk":
            return {"status": "ignored", "reason": "unsupported_subject"}

        result = await self.embedding_service.queue_for_chunk(envelope.subject.id)
        return {
            "status": "queued",
            "embedding_id": result.record.id,
            "operation": result.operation,
        }

    async def handle_embedding_requested(
        self, envelope: PipelineEventEnvelope
    ) -> dict[str, str]:
        if envelope.event_type != "embedding.requested":
            return {"status": "ignored", "reason": "unsupported_event_type"}
        if envelope.subject.type != "embedding_record":
            return {"status": "ignored", "reason": "unsupported_subject"}

        record = await self.embedding_service.complete(envelope.subject.id)
        return {
            "status": "completed",
            "embedding_id": record.id,
        }
