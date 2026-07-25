from __future__ import annotations

from dataclasses import dataclass

from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.normalization.repositories import (
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
)

from .publishers import SourceChunkPublisher
from .repositories import InMemorySourceChunkRepository
from .source_aware import SourceAwareChunker


@dataclass(frozen=True)
class ChunkingServiceResult:
    status: str
    source_chunk_count: int = 0
    published_count: int = 0
    reason: str | None = None


class ChunkingService:
    def __init__(
        self,
        *,
        source_objects: InMemorySourceObjectRepository,
        source_files: InMemorySourceFileRepository,
        source_chunks: InMemorySourceChunkRepository,
        chunker: SourceAwareChunker,
        publisher: SourceChunkPublisher,
    ) -> None:
        self.source_objects = source_objects
        self.source_files = source_files
        self.source_chunks = source_chunks
        self.chunker = chunker
        self.publisher = publisher

    async def handle_source_object_upserted(
        self, envelope: PipelineEventEnvelope
    ) -> ChunkingServiceResult:
        if envelope.event_type != "source_object.upserted":
            return ChunkingServiceResult("ignored", reason="unsupported_event_type")
        source_object = self.source_objects.get_by_id(envelope.subject.id)
        chunks = self.chunker.chunks_for_source_object(source_object)
        upserts = self.source_chunks.upsert_many(chunks)
        self.source_chunks.mark_stale_replaced_by(
            workspace_id=source_object.workspace_id,
            source_object_id=source_object.id,
            active_ids={result.record.id for result in upserts},
        )
        published = 0
        for result in upserts:
            if result.operation == "noop":
                continue
            await self.publisher.publish_upserted(
                result.record,
                source_object_event_id=envelope.event_id,
                operation=result.operation,
            )
            published += 1
        return ChunkingServiceResult("processed", len(upserts), published)

    async def handle_source_file_fetched(
        self, envelope: PipelineEventEnvelope
    ) -> ChunkingServiceResult:
        if envelope.event_type != "source_file.fetched":
            return ChunkingServiceResult("ignored", reason="unsupported_event_type")
        source_file = self.source_files.get_by_id(envelope.subject.id)
        if source_file.source_object_id is None:
            return ChunkingServiceResult("ignored", reason="missing_source_object")
        source_object = self.source_objects.get_by_id(source_file.source_object_id)
        upserts = self.source_chunks.upsert_many(
            self.chunker.chunks_for_source_file(source_object, source_file)
        )
        published = 0
        for result in upserts:
            if result.operation == "noop":
                continue
            await self.publisher.publish_upserted(
                result.record,
                source_object_event_id=envelope.event_id,
                operation=result.operation,
            )
            published += 1
        return ChunkingServiceResult("processed", len(upserts), published)
