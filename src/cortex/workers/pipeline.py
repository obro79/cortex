from __future__ import annotations

from dataclasses import dataclass

from cortex.chunking.service import ChunkingService
from cortex.events.in_memory import InMemoryEventBus
from cortex.normalization.service import SourceNormalizationService
from cortex.workers.embeddings import EmbeddingWorkerSkeleton
from cortex.workers.indexing import IndexWorker


@dataclass(frozen=True)
class PipelineDrainResult:
    processed_event_count: int
    normalization_count: int = 0
    chunking_count: int = 0
    embedding_count: int = 0
    indexing_count: int = 0


class InMemoryPipelineDispatcher:
    def __init__(
        self,
        *,
        normalization: SourceNormalizationService,
        chunking: ChunkingService,
        embeddings: EmbeddingWorkerSkeleton,
        indexing: IndexWorker | None = None,
    ) -> None:
        self.normalization = normalization
        self.chunking = chunking
        self.embeddings = embeddings
        self.indexing = indexing
        self._cursor = 0

    async def drain(self, event_bus: InMemoryEventBus) -> PipelineDrainResult:
        normalization_count = 0
        chunking_count = 0
        embedding_count = 0
        indexing_count = 0
        processed_event_count = 0

        while self._cursor < len(event_bus.events):
            envelope = event_bus.events[self._cursor]
            self._cursor += 1
            processed_event_count += 1

            if envelope.event_type == "raw_event.persisted":
                normalization_result = (
                    await self.normalization.handle_raw_event_persisted(envelope)
                )
                if normalization_result.status == "processed":
                    normalization_count += normalization_result.source_object_count
            elif envelope.event_type == "source_object.upserted":
                chunking_result = await self.chunking.handle_source_object_upserted(
                    envelope
                )
                if chunking_result.status == "processed":
                    chunking_count += chunking_result.source_chunk_count
            elif envelope.event_type == "source_file.fetched":
                file_chunking_result = await self.chunking.handle_source_file_fetched(
                    envelope
                )
                if file_chunking_result.status == "processed":
                    chunking_count += file_chunking_result.source_chunk_count
            elif envelope.event_type == "source_chunk.upserted":
                queue_result = await self.embeddings.handle_source_chunk_upserted(
                    envelope
                )
                if queue_result["status"] == "queued":
                    embedding_count += 1
            elif envelope.event_type == "embedding.requested":
                embedding_result = await self.embeddings.handle_embedding_requested(
                    envelope
                )
                if embedding_result["status"] == "completed":
                    embedding_count += 1
            elif envelope.event_type == "embedding.completed" and self.indexing:
                index_result = await self.indexing.handle_embedding_completed(envelope)
                if index_result["status"] == "queued":
                    indexing_count += 1
            elif envelope.event_type == "index.requested" and self.indexing:
                index_result = await self.indexing.handle_index_requested(envelope)
                if index_result["status"] == "completed":
                    indexing_count += 1

        return PipelineDrainResult(
            processed_event_count=processed_event_count,
            normalization_count=normalization_count,
            chunking_count=chunking_count,
            embedding_count=embedding_count,
            indexing_count=indexing_count,
        )
