from __future__ import annotations

from cortex.contracts.entities import IndexJob

from .publishers import IndexPublisher
from .repositories import IndexJobUpsertResult, InMemoryIndexJobRepository


class IndexJobService:
    def __init__(
        self, repository: InMemoryIndexJobRepository, publisher: IndexPublisher
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
        result = self.repository.enqueue(
            workspace_id=workspace_id,
            target_store=target_store,
            target_type="source_chunk",
            target_id=source_chunk_id,
            operation=operation,
            index_version=index_version,
        )
        if result.operation != "noop":
            await self.publisher.publish_requested(result.record)
        return result

    async def complete(self, index_job_id: str) -> IndexJob:
        completed = self.repository.mark_completed(index_job_id)
        await self.publisher.publish_completed(completed)
        return completed
