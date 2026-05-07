from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cortex.contracts.entities import SourceFile, SourceObject
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


class SourceObjectPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_upserted(
        self,
        source_object: SourceObject,
        *,
        raw_event_id: str,
        payload_hash: str | None,
        operation: str,
        parent_event_id: str | None = None,
        file_count: int = 0,
        relationship_count: int = 0,
    ) -> PipelineEventEnvelope:
        envelope = PipelineEventEnvelope(
            event_id=f"evt_so_{uuid4().hex}",
            event_type="source_object.upserted",
            occurred_at=source_object.occurred_at,
            published_at=datetime.now(UTC),
            workspace_id=source_object.workspace_id,
            source_connection_id=source_object.source_connection_id,
            provider=source_object.provider,
            partition_key=f"{source_object.workspace_id}:{source_object.external_object_key}",
            external_object_key=source_object.external_object_key,
            subject=PipelineSubject(type="source_object", id=source_object.id),
            causation=PipelineCausation(
                raw_event_id=raw_event_id,
                source_object_id=source_object.id,
            ),
            versions=PipelineVersions(
                normalized_version=source_object.normalized_version
            ),
            hashes=PipelineHashes(
                payload_hash=payload_hash,
                content_hash=source_object.content_hash,
            ),
            trace=PipelineTrace(
                trace_id=source_object.trace_id or f"trace_{source_object.id}",
                parent_event_id=parent_event_id,
            ),
            producer=PipelineProducer(service="normalization", instance_id="local"),
            payload={
                "object_type": source_object.object_type,
                "operation": operation,
                "file_count": file_count,
                "relationship_count": relationship_count,
            },
        )
        await self.event_bus.publish(envelope)
        return envelope


class SourceFilePublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def publish_fetched(
        self,
        source_file: SourceFile,
        *,
        raw_event_id: str,
        source_object_id: str | None,
        payload_hash: str | None,
        operation: str,
        parent_event_id: str | None = None,
    ) -> PipelineEventEnvelope:
        envelope = PipelineEventEnvelope(
            event_id=f"evt_file_{uuid4().hex}",
            event_type="source_file.fetched",
            published_at=datetime.now(UTC),
            workspace_id=source_file.workspace_id,
            source_connection_id=source_file.source_connection_id,
            provider=source_file.provider,
            partition_key=f"{source_file.workspace_id}:{source_file.external_object_key}",
            external_object_key=source_file.external_object_key,
            subject=PipelineSubject(type="source_file", id=source_file.id),
            causation=PipelineCausation(
                raw_event_id=raw_event_id,
                source_object_id=source_object_id,
            ),
            hashes=PipelineHashes(
                payload_hash=payload_hash,
                content_hash=source_file.content_hash,
            ),
            trace=PipelineTrace(
                trace_id=source_file.trace_id or f"trace_{source_file.id}",
                parent_event_id=parent_event_id,
            ),
            producer=PipelineProducer(service="normalization", instance_id="local"),
            payload={
                "content_type": source_file.content_type,
                "operation": operation,
            },
        )
        await self.event_bus.publish(envelope)
        return envelope
