from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from cortex.contracts.entities import EmbeddingRecord
from cortex.contracts.enums import EmbeddingJobStatus


@dataclass(frozen=True)
class EmbeddingUpsertResult:
    record: EmbeddingRecord
    operation: str


class InMemoryEmbeddingRecordRepository:
    def __init__(self) -> None:
        self._records: dict[str, EmbeddingRecord] = {}
        self._by_chunk_version: dict[tuple[str, str, str], str] = {}

    def queue_for_chunk(
        self,
        *,
        workspace_id: str,
        source_chunk_id: str,
        provider: str,
        model: str,
        dimensions: int,
        task_type: str,
        embedding_version: str,
        chunking_version: str,
        input_text_hash: str,
    ) -> EmbeddingUpsertResult:
        key = (workspace_id, source_chunk_id, embedding_version)
        existing_id = self._by_chunk_version.get(key)
        if existing_id:
            existing = self._records[existing_id]
            if existing.input_text_hash == input_text_hash:
                return EmbeddingUpsertResult(existing, "noop")
        now = datetime.now(UTC)
        record = EmbeddingRecord(
            id=f"emb_{source_chunk_id}_{embedding_version}".replace("-", "_"),
            workspace_id=workspace_id,
            source_chunk_id=source_chunk_id,
            provider=provider,
            model=model,
            dimensions=dimensions,
            task_type=task_type,
            embedding_version=embedding_version,
            chunking_version=chunking_version,
            input_text_hash=input_text_hash,
            status=EmbeddingJobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        if existing_id:
            record = record.model_copy(
                update={
                    "id": existing_id,
                    "created_at": self._records[existing_id].created_at,
                }
            )
            operation = "updated"
        else:
            self._by_chunk_version[key] = record.id
            operation = "inserted"
        self._records[record.id] = record
        return EmbeddingUpsertResult(record, operation)

    def get_by_id(self, embedding_id: str) -> EmbeddingRecord:
        return self._records[embedding_id]

    def mark_completed(
        self, embedding_id: str, *, vector_hash: str, collection: str | None = None
    ) -> EmbeddingRecord:
        current = self.get_by_id(embedding_id)
        updated = current.model_copy(
            update={
                "status": EmbeddingJobStatus.COMPLETED,
                "vector_hash": vector_hash,
                "qdrant_collection": collection,
                "qdrant_point_id": embedding_id,
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[embedding_id] = updated
        return updated

    def mark_failed_retryable(
        self, embedding_id: str, error_code: str, error_message: str
    ) -> EmbeddingRecord:
        current = self.get_by_id(embedding_id)
        updated = current.model_copy(
            update={
                "status": EmbeddingJobStatus.FAILED_RETRYABLE,
                "attempt_count": current.attempt_count + 1,
                "last_attempt_at": datetime.now(UTC),
                "last_error_code": error_code,
                "last_error_message": error_message,
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[embedding_id] = updated
        return updated
