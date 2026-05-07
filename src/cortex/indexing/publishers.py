from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import IndexJob
from cortex.contracts.pipeline_events import (
    PipelineEventEnvelope,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
)
from cortex.events.bus import EventBus


class IndexPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_requested(self, job: IndexJob) -> PipelineEventEnvelope:
        envelope = self._envelope("index.requested", job)
        await self.event_bus.publish(envelope)
        return envelope

    async def publish_completed(self, job: IndexJob) -> PipelineEventEnvelope:
        envelope = self._envelope("index.completed", job)
        await self.event_bus.publish(envelope)
        return envelope

    def _envelope(self, event_type: str, job: IndexJob) -> PipelineEventEnvelope:
        return PipelineEventEnvelope(
            event_id=f"evt_index_{uuid4().hex}",
            event_type=event_type,
            published_at=datetime.now(UTC),
            workspace_id=job.workspace_id,
            partition_key=f"{job.workspace_id}:{job.target_id}",
            subject=PipelineSubject(type="index_job", id=job.id),
            trace=PipelineTrace(trace_id=job.trace_id or f"trace_{job.id}"),
            producer=PipelineProducer(service="indexing", instance_id="local"),
            payload={
                "target_store": job.target_store,
                "target_type": job.target_type,
                "operation": job.operation,
                "index_version": job.index_version,
                "status": job.status,
            },
        )
