from __future__ import annotations

from typing import Any, cast

from cortex.contracts.entities import EmbeddingRecord
from cortex.utils.asyncio import maybe_await

from .deterministic import DeterministicEmbeddingProvider
from .publishers import EmbeddingPublisher
from .repositories import EmbeddingUpsertResult


class EmbeddingService:
    def __init__(
        self,
        *,
        source_chunks: Any,
        embeddings: Any,
        provider: DeterministicEmbeddingProvider,
        publisher: EmbeddingPublisher,
        model: str = "fixture-vector-v1",
    ) -> None:
        self.source_chunks = source_chunks
        self.embeddings = embeddings
        self.provider = provider
        self.publisher = publisher
        self.model = model

    async def queue_for_chunk(self, source_chunk_id: str) -> EmbeddingUpsertResult:
        chunk = await maybe_await(self.source_chunks.get_by_id(source_chunk_id))
        result = cast(
            EmbeddingUpsertResult,
            await maybe_await(
                self.embeddings.queue_for_chunk(
                    workspace_id=chunk.workspace_id,
                    source_chunk_id=chunk.id,
                    provider="deterministic",
                    model=self.model,
                    dimensions=self.provider.dimensions,
                    task_type="retrieval_document",
                    embedding_version=self.provider.version,
                    chunking_version=chunk.chunking_version,
                    input_text_hash=chunk.text_hash,
                )
            ),
        )
        if result.operation != "noop":
            await self.publisher.publish_requested(result.record)
        return result

    async def complete(self, embedding_id: str) -> EmbeddingRecord:
        record = await maybe_await(self.embeddings.get_by_id(embedding_id))
        output = self.provider.embed(record.input_text_hash)
        completed = cast(
            EmbeddingRecord,
            await maybe_await(
                self.embeddings.mark_completed(
                    embedding_id,
                    vector_hash=output.vector_hash,
                    collection="fixture-cortex-dev",
                )
            ),
        )
        await self.publisher.publish_completed(completed)
        return completed
