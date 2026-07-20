from __future__ import annotations

from typing import Any, cast

from cortex.contracts.entities import EmbeddingRecord, IndexJob
from cortex.utils.asyncio import maybe_await

from .publishers import IndexPublisher
from .repositories import IndexJobUpsertResult, InMemoryIndexJobRepository


class IndexJobService:
    def __init__(
        self, repository: InMemoryIndexJobRepository | Any, publisher: IndexPublisher
    ) -> None:
        self.repository = repository
        self.publisher = publisher

    async def enqueue_for_chunk(
        self,
        *,
        workspace_id: str,
        source_chunk_id: str,
        target_store: str,
        operation: str = "upsert",
        index_version: str = "index-v1",
    ) -> IndexJobUpsertResult:
        result = cast(
            IndexJobUpsertResult,
            await maybe_await(
                self.repository.enqueue(
                    workspace_id=workspace_id,
                    target_store=target_store,
                    target_type="source_chunk",
                    target_id=source_chunk_id,
                    operation=operation,
                    index_version=index_version,
                )
            ),
        )
        if result.operation != "noop":
            await self.publisher.publish_requested(result.record)
        return result

    async def enqueue_for_embedding(
        self,
        embedding: EmbeddingRecord,
        *,
        operation: str = "upsert",
        index_version: str = "qdrant-v1",
        trace_id: str | None = None,
    ) -> IndexJobUpsertResult:
        """Queue a content-addressed Qdrant write for one completed embedding.

        The durable embedding id keeps the Qdrant point stable while the vector
        hash in the job identity makes a changed chunk/vector a new delivery.
        """
        if operation != "delete" and embedding.vector_hash is None:
            raise ValueError("completed embedding vector_hash is required")
        vector_hash = embedding.vector_hash or "deleted"
        result = cast(
            IndexJobUpsertResult,
            await maybe_await(
                self.repository.enqueue(
                    workspace_id=embedding.workspace_id,
                    target_store="qdrant",
                    target_type="embedding_record",
                    target_id=embedding.id,
                    operation=operation,
                    index_version=f"{index_version}:{vector_hash}",
                    trace_id=trace_id,
                )
            ),
        )
        if result.operation != "noop":
            await self.publisher.publish_requested(result.record)
        return result

    async def complete(self, index_job_id: str) -> IndexJob:
        completed = cast(
            IndexJob,
            await maybe_await(self.repository.mark_completed(index_job_id)),
        )
        await self.publisher.publish_completed(completed)
        return completed
