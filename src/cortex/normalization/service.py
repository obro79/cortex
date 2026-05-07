from __future__ import annotations

from dataclasses import dataclass

from cortex.contracts.enums import RawEventStatus
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadNotFoundError
from cortex.ingestion.raw_events import (
    InMemoryRawEventRepository,
    RawEventNotFoundError,
)

from .publishers import SourceFilePublisher, SourceObjectPublisher
from .registry import NormalizerRegistry
from .repositories import (
    InMemoryRelationshipSeedRepository,
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
)


@dataclass(frozen=True)
class NormalizationServiceResult:
    status: str
    raw_event_id: str | None = None
    source_object_count: int = 0
    source_file_count: int = 0
    relationship_seed_count: int = 0
    published_count: int = 0
    reason: str | None = None


class SourceNormalizationService:
    def __init__(
        self,
        *,
        raw_events: InMemoryRawEventRepository,
        payload_store: InMemoryPayloadStore,
        source_objects: InMemorySourceObjectRepository,
        source_files: InMemorySourceFileRepository,
        relationship_seeds: InMemoryRelationshipSeedRepository,
        source_object_publisher: SourceObjectPublisher,
        source_file_publisher: SourceFilePublisher,
        registry: NormalizerRegistry | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.raw_events = raw_events
        self.payload_store = payload_store
        self.source_objects = source_objects
        self.source_files = source_files
        self.relationship_seeds = relationship_seeds
        self.source_object_publisher = source_object_publisher
        self.source_file_publisher = source_file_publisher
        self.registry = registry or NormalizerRegistry()
        self.max_attempts = max_attempts

    async def handle_raw_event_persisted(
        self, envelope: PipelineEventEnvelope
    ) -> NormalizationServiceResult:
        if envelope.event_type != "raw_event.persisted":
            return NormalizationServiceResult(
                status="ignored", reason="unsupported_event_type"
            )
        if envelope.subject.type != "raw_event":
            return NormalizationServiceResult(
                status="ignored", reason="unsupported_subject"
            )

        try:
            raw_event = self.raw_events.get_by_id(envelope.subject.id)
        except RawEventNotFoundError:
            return NormalizationServiceResult(
                status="retryable", reason="raw_event_not_found"
            )
        if raw_event.status == RawEventStatus.DELETED:
            return NormalizationServiceResult(
                status="ignored", raw_event_id=raw_event.id, reason="raw_event_deleted"
            )

        try:
            if raw_event.status != RawEventStatus.PROCESSED:
                self.raw_events.mark_processing(raw_event.id)
            if raw_event.payload_ref is None:
                raise PayloadNotFoundError("<missing>")
            payload_bytes = self.payload_store.get(raw_event.payload_ref)
            normalizer = self.registry.resolve(raw_event)
            result = normalizer(raw_event, payload_bytes)
            object_results = self.source_objects.upsert_many(result.source_objects)
            file_results = self.source_files.upsert_many(result.source_files)
            seed_results = self.relationship_seeds.upsert_many(
                result.relationship_seeds
            )

            published_count = 0
            for object_result in object_results:
                if (
                    object_result.operation == "noop"
                    and raw_event.status == RawEventStatus.PROCESSED
                ):
                    continue
                await self.source_object_publisher.publish_upserted(
                    object_result.record,
                    raw_event_id=raw_event.id,
                    payload_hash=raw_event.payload_hash,
                    operation=object_result.operation,
                    parent_event_id=envelope.event_id,
                    file_count=len(result.source_files),
                    relationship_count=len(result.relationship_seeds),
                )
                published_count += 1
            for file_result in file_results:
                if (
                    file_result.operation == "noop"
                    and raw_event.status == RawEventStatus.PROCESSED
                ):
                    continue
                await self.source_file_publisher.publish_fetched(
                    file_result.record,
                    raw_event_id=raw_event.id,
                    source_object_id=file_result.record.source_object_id,
                    payload_hash=raw_event.payload_hash,
                    operation=file_result.operation,
                    parent_event_id=envelope.event_id,
                )
                published_count += 1
            if raw_event.status != RawEventStatus.PROCESSED:
                self.raw_events.mark_processed(raw_event.id)
            return NormalizationServiceResult(
                status="processed",
                raw_event_id=raw_event.id,
                source_object_count=len(object_results),
                source_file_count=len(file_results),
                relationship_seed_count=len(seed_results),
                published_count=published_count,
            )
        except Exception as error:
            current = self.raw_events.get_by_id(raw_event.id)
            if current.attempt_count + 1 >= self.max_attempts:
                self.raw_events.mark_deadlettered(
                    raw_event.id,
                    "normalization_failed",
                    str(error),
                )
                return NormalizationServiceResult(
                    status="deadlettered",
                    raw_event_id=raw_event.id,
                    reason="normalization_failed",
                )
            self.raw_events.mark_failed_retryable(
                raw_event.id,
                "normalization_failed",
                str(error),
            )
            return NormalizationServiceResult(
                status="retryable",
                raw_event_id=raw_event.id,
                reason="normalization_failed",
            )
