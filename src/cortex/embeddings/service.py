from __future__ import annotations

from typing import Any, cast

from cortex.contracts.entities import EmbeddingRecord
from cortex.platform.rate_limits import (
    RateLimitPolicy,
    RateLimitService,
    RateLimitSubject,
)
from cortex.utils.asyncio import maybe_await

from .deterministic import EmbeddingProvider
from .publishers import EmbeddingPublisher
from .repositories import EmbeddingUpsertResult


class EmbeddingService:
    def __init__(
        self,
        *,
        source_chunks: Any,
        embeddings: Any,
        provider: EmbeddingProvider,
        publisher: EmbeddingPublisher,
        model_rate_limiter: RateLimitService | None = None,
        model_rate_limit_policy: RateLimitPolicy | None = None,
    ) -> None:
        self.source_chunks = source_chunks
        self.embeddings = embeddings
        self.provider = provider
        self.publisher = publisher
        self.model_rate_limiter = model_rate_limiter
        self.model_rate_limit_policy = model_rate_limit_policy

    async def queue_for_chunk(self, source_chunk_id: str) -> EmbeddingUpsertResult:
        chunk = await maybe_await(self.source_chunks.get_by_id(source_chunk_id))
        result = cast(
            EmbeddingUpsertResult,
            await maybe_await(
                self.embeddings.queue_for_chunk(
                    workspace_id=chunk.workspace_id,
                    source_chunk_id=chunk.id,
                    provider=self.provider.provider_name,
                    model=self.provider.model,
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
        if self.model_rate_limiter and self.model_rate_limit_policy:
            self.model_rate_limiter.enforce(
                self.model_rate_limit_policy,
                RateLimitSubject(
                    workspace_id=record.workspace_id,
                    user_id=f"model:{self.provider.model}",
                    client_id="embedding-worker",
                ),
            )
        chunk = await maybe_await(self.source_chunks.get_by_id(record.source_chunk_id))
        output = await maybe_await(
            self.provider.embed(record.input_text_hash, chunk.text)
        )
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
