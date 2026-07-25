from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.contracts.entities import EmbeddingRecord
from cortex.contracts.enums import EmbeddingJobStatus
from cortex.db.models import EmbeddingRecordRecord


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


def embedding_record_from_record(record: EmbeddingRecordRecord) -> EmbeddingRecord:
    return EmbeddingRecord(
        id=record.id,
        workspace_id=record.workspace_id,
        source_chunk_id=record.source_chunk_id,
        provider=record.provider,
        model=record.model,
        dimensions=record.dimensions,
        task_type=record.task_type,
        embedding_version=record.embedding_version,
        chunking_version=record.chunking_version,
        input_text_hash=record.input_text_hash,
        vector_hash=record.vector_hash,
        qdrant_collection=record.qdrant_collection,
        qdrant_point_id=record.qdrant_point_id,
        status=EmbeddingJobStatus(record.status),
        model_invocation_id=record.model_invocation_id,
        attempt_count=record.attempt_count,
        last_error_code=record.last_error_code,
        last_error_message=record.last_error_message,
        next_retry_at=record.next_retry_at,
        last_attempt_at=record.last_attempt_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyEmbeddingRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def queue_for_chunk(
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
        existing = await self._get_by_chunk_version(
            workspace_id, source_chunk_id, embedding_version
        )
        if existing and existing.input_text_hash == input_text_hash:
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
        if existing:
            record = record.model_copy(
                update={"id": existing.id, "created_at": existing.created_at}
            )
            await self._apply_update(record)
            return EmbeddingUpsertResult(record, "updated")
        self.session.add(self._record_from_embedding(record))
        await self.session.flush()
        return EmbeddingUpsertResult(record, "inserted")

    async def get_by_id(self, embedding_id: str) -> EmbeddingRecord:
        record = await self.session.get(EmbeddingRecordRecord, embedding_id)
        if record is None:
            raise KeyError(embedding_id)
        return embedding_record_from_record(record)

    async def mark_completed(
        self, embedding_id: str, *, vector_hash: str, collection: str | None = None
    ) -> EmbeddingRecord:
        current = await self.get_by_id(embedding_id)
        updated = current.model_copy(
            update={
                "status": EmbeddingJobStatus.COMPLETED,
                "vector_hash": vector_hash,
                "qdrant_collection": collection,
                "qdrant_point_id": embedding_id,
                "updated_at": datetime.now(UTC),
            }
        )
        await self._apply_update(updated)
        return updated

    async def mark_failed_retryable(
        self, embedding_id: str, error_code: str, error_message: str
    ) -> EmbeddingRecord:
        current = await self.get_by_id(embedding_id)
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
        await self._apply_update(updated)
        return updated

    async def _get_by_chunk_version(
        self, workspace_id: str, source_chunk_id: str, embedding_version: str
    ) -> EmbeddingRecord | None:
        result = await self.session.execute(
            select(EmbeddingRecordRecord).where(
                EmbeddingRecordRecord.workspace_id == workspace_id,
                EmbeddingRecordRecord.source_chunk_id == source_chunk_id,
                EmbeddingRecordRecord.embedding_version == embedding_version,
            )
        )
        record = result.scalar_one_or_none()
        return embedding_record_from_record(record) if record else None

    async def _apply_update(self, embedding: EmbeddingRecord) -> None:
        record = await self.session.get(EmbeddingRecordRecord, embedding.id)
        if record is None:
            raise KeyError(embedding.id)
        record.provider = embedding.provider
        record.model = embedding.model
        record.dimensions = embedding.dimensions
        record.task_type = embedding.task_type
        record.embedding_version = embedding.embedding_version
        record.chunking_version = embedding.chunking_version
        record.input_text_hash = embedding.input_text_hash
        record.vector_hash = embedding.vector_hash
        record.qdrant_collection = embedding.qdrant_collection
        record.qdrant_point_id = embedding.qdrant_point_id
        record.status = EmbeddingJobStatus(embedding.status).value
        record.model_invocation_id = embedding.model_invocation_id
        record.attempt_count = embedding.attempt_count
        record.last_error_code = embedding.last_error_code
        record.last_error_message = embedding.last_error_message
        record.next_retry_at = embedding.next_retry_at
        record.last_attempt_at = embedding.last_attempt_at
        record.updated_at = embedding.updated_at
        await self.session.flush()

    def _record_from_embedding(
        self, embedding: EmbeddingRecord
    ) -> EmbeddingRecordRecord:
        return EmbeddingRecordRecord(
            id=embedding.id,
            workspace_id=embedding.workspace_id,
            source_chunk_id=embedding.source_chunk_id,
            provider=embedding.provider,
            model=embedding.model,
            dimensions=embedding.dimensions,
            task_type=embedding.task_type,
            embedding_version=embedding.embedding_version,
            chunking_version=embedding.chunking_version,
            input_text_hash=embedding.input_text_hash,
            vector_hash=embedding.vector_hash,
            qdrant_collection=embedding.qdrant_collection,
            qdrant_point_id=embedding.qdrant_point_id,
            status=EmbeddingJobStatus(embedding.status).value,
            model_invocation_id=embedding.model_invocation_id,
            attempt_count=embedding.attempt_count,
            last_error_code=embedding.last_error_code,
            last_error_message=embedding.last_error_message,
            next_retry_at=embedding.next_retry_at,
            last_attempt_at=embedding.last_attempt_at,
            created_at=embedding.created_at,
            updated_at=embedding.updated_at,
        )
