from __future__ import annotations

from typing import Any, cast

from cortex.contracts.entities import EmbeddingRecord, IndexJob, SourceChunk
from cortex.contracts.enums import EmbeddingJobStatus, IndexJobStatus
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.embeddings.deterministic import EmbeddingProvider
from cortex.indexing.service import IndexJobService
from cortex.interfaces.vector_index import VectorIndex
from cortex.utils.asyncio import maybe_await


class IndexWorker:
    """Turns durable embedding records into idempotent derived-vector writes."""

    def __init__(
        self,
        *,
        index_service: IndexJobService,
        embeddings: Any,
        source_chunks: Any,
        embedding_provider: EmbeddingProvider,
        vector_index: VectorIndex | None,
        index_version: str = "qdrant-v1",
    ) -> None:
        self.index_service = index_service
        self.embeddings = embeddings
        self.source_chunks = source_chunks
        self.embedding_provider = embedding_provider
        self.vector_index = vector_index
        self.index_version = index_version

    async def handle_embedding_completed(
        self, envelope: PipelineEventEnvelope
    ) -> dict[str, str]:
        if envelope.event_type != "embedding.completed":
            return {"status": "ignored", "reason": "unsupported_event_type"}
        if envelope.subject.type != "embedding_record":
            return {"status": "ignored", "reason": "unsupported_subject"}
        try:
            embedding = cast(
                EmbeddingRecord,
                await maybe_await(self.embeddings.get_by_id(envelope.subject.id)),
            )
        except KeyError:
            return {"status": "retryable", "reason": "embedding_not_found"}
        if embedding.workspace_id != envelope.workspace_id:
            return {"status": "ignored", "reason": "workspace_mismatch"}
        if embedding.status != EmbeddingJobStatus.COMPLETED:
            return {"status": "retryable", "reason": "embedding_not_completed"}
        result = await self.index_service.enqueue_for_embedding(
            embedding,
            index_version=self.index_version,
            trace_id=envelope.trace.trace_id,
        )
        return {
            "status": "queued",
            "index_job_id": result.record.id,
            "operation": result.operation,
        }

    async def handle_index_requested(
        self, envelope: PipelineEventEnvelope
    ) -> dict[str, str]:
        if envelope.event_type != "index.requested":
            return {"status": "ignored", "reason": "unsupported_event_type"}
        if envelope.subject.type != "index_job":
            return {"status": "ignored", "reason": "unsupported_subject"}
        try:
            job = cast(
                IndexJob,
                await maybe_await(
                    self.index_service.repository.get_by_id(envelope.subject.id)
                ),
            )
        except KeyError:
            return {"status": "retryable", "reason": "index_job_not_found"}
        if job.workspace_id != envelope.workspace_id:
            return {"status": "ignored", "reason": "workspace_mismatch"}
        if job.status == IndexJobStatus.COMPLETED:
            return {"status": "completed", "index_job_id": job.id, "operation": "noop"}
        if job.target_store != "qdrant" or job.target_type != "embedding_record":
            return {"status": "ignored", "reason": "unsupported_index_target"}

        try:
            await maybe_await(self.index_service.repository.mark_processing(job.id))
            await self._deliver(job)
            completed = await self.index_service.complete(job.id)
        except Exception as error:
            failed = cast(
                IndexJob,
                await maybe_await(
                    self.index_service.repository.mark_failed_retryable(
                        job.id,
                        self._error_code(error),
                        type(error).__name__,
                    )
                ),
            )
            return {
                "status": "retryable",
                "index_job_id": failed.id,
                "reason": failed.last_error_code or "index_delivery_failed",
            }
        return {"status": "completed", "index_job_id": completed.id}

    async def _deliver(self, job: IndexJob) -> None:
        if self.vector_index is None:
            raise RuntimeError("vector_index_unconfigured")
        embedding = cast(
            EmbeddingRecord,
            await maybe_await(self.embeddings.get_by_id(job.target_id)),
        )
        if embedding.workspace_id != job.workspace_id:
            raise PermissionError("workspace_mismatch")
        collection = embedding.qdrant_collection
        point_id = embedding.qdrant_point_id or embedding.id
        if collection is None:
            raise ValueError("embedding_collection_missing")
        if not await self.vector_index.health():
            raise RuntimeError("vector_index_unready")
        if job.operation == "delete":
            await self.vector_index.delete(collection, point_id)
            return
        if job.operation not in {"upsert", "rebuild"}:
            raise ValueError("unsupported_index_operation")
        if embedding.status != EmbeddingJobStatus.COMPLETED:
            raise ValueError("embedding_not_completed")
        chunk = cast(
            SourceChunk,
            await maybe_await(self.source_chunks.get_by_id(embedding.source_chunk_id)),
        )
        if chunk.workspace_id != embedding.workspace_id:
            raise PermissionError("workspace_mismatch")
        output = await maybe_await(
            self.embedding_provider.embed(embedding.input_text_hash, chunk.text)
        )
        if output.vector_hash != embedding.vector_hash:
            raise ValueError("embedding_vector_hash_mismatch")
        if len(output.vector) != embedding.dimensions:
            raise ValueError("embedding_dimensions_mismatch")
        await self.vector_index.ensure_collection(collection, embedding.dimensions)
        await self.vector_index.upsert(
            collection,
            point_id,
            output.vector,
            self._payload(chunk, embedding),
        )

    @staticmethod
    def _payload(chunk: SourceChunk, embedding: EmbeddingRecord) -> dict[str, Any]:
        metadata = chunk.metadata_json
        payload: dict[str, Any] = {
            "workspace_id": chunk.workspace_id,
            "source_object_id": chunk.source_object_id,
            "source_chunk_id": chunk.id,
            "chunk_type": chunk.chunk_type,
            "chunking_version": chunk.chunking_version,
            "embedding_model": embedding.model,
            "embedding_version": embedding.embedding_version,
            "status": str(chunk.status),
        }
        for key in ("provider", "source_type", "source_allowlist_eligible"):
            value = metadata.get(key)
            if isinstance(value, str | bool):
                payload[key] = value
        return payload

    @staticmethod
    def _error_code(error: Exception) -> str:
        message = str(error)
        if message in {
            "vector_index_unconfigured",
            "vector_index_unready",
            "embedding_vector_hash_mismatch",
            "embedding_dimensions_mismatch",
            "embedding_collection_missing",
            "embedding_not_completed",
        }:
            return message
        return "index_delivery_failed"
