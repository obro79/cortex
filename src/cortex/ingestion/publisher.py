from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import RawEvent
from cortex.contracts.pipeline_events import (
    PipelineCausation,
    PipelineEventEnvelope,
    PipelineHashes,
    PipelineProducer,
    PipelineSubject,
    PipelineTrace,
)
from cortex.events.bus import EventBus


class RawEventPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_persisted(
        self,
        raw_event: RawEvent,
        *,
        replay_metadata: dict[str, str] | None = None,
    ) -> PipelineEventEnvelope:
        event = self.build_persisted_envelope(
            raw_event,
            replay_metadata=replay_metadata,
        )
        await self.event_bus.publish(event)
        return event

    def build_persisted_envelope(
        self,
        raw_event: RawEvent,
        *,
        replay_metadata: dict[str, str] | None = None,
    ) -> PipelineEventEnvelope:
        provider_event_type = raw_event.event_type
        payload = {"provider_event_type": provider_event_type}
        if replay_metadata:
            payload.update(replay_metadata)
        return PipelineEventEnvelope(
            event_id=f"evt_raw_{uuid4().hex}",
            event_type="raw_event.persisted",
            occurred_at=raw_event.occurred_at,
            published_at=datetime.now(UTC),
            workspace_id=raw_event.workspace_id,
            source_connection_id=raw_event.source_connection_id,
            provider=raw_event.provider,
            partition_key=f"{raw_event.workspace_id}:{raw_event.external_object_key}",
            external_object_key=raw_event.external_object_key,
            subject=PipelineSubject(type="raw_event", id=raw_event.id),
            causation=PipelineCausation(raw_event_id=raw_event.id),
            hashes=PipelineHashes(payload_hash=raw_event.payload_hash),
            trace=PipelineTrace(trace_id=raw_event.trace_id or f"trace_{raw_event.id}"),
            producer=PipelineProducer(
                service="raw-event-ingestion", instance_id="local"
            ),
            payload=payload,
        )
