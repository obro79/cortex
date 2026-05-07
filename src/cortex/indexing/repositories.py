from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from cortex.contracts.entities import IndexJob
from cortex.contracts.enums import IndexJobStatus


@dataclass(frozen=True)
class IndexJobUpsertResult:
    record: IndexJob
    operation: str


class InMemoryIndexJobRepository:
    def __init__(self) -> None:
        self._records: dict[str, IndexJob] = {}
        self._by_identity: dict[tuple[str, str, str, str, str, str], str] = {}

    def enqueue(
        self,
        *,
        workspace_id: str,
        target_store: str,
        target_type: str,
        target_id: str,
        operation: str,
        index_version: str,
        trace_id: str | None = None,
    ) -> IndexJobUpsertResult:
        key = (
            workspace_id,
            target_store,
            target_type,
            target_id,
            operation,
            index_version,
        )
        existing_id = self._by_identity.get(key)
        if existing_id:
            return IndexJobUpsertResult(self._records[existing_id], "noop")
        now = datetime.now(UTC)
        record = IndexJob(
            id=f"idx_{target_store}_{target_type}_{target_id}_{operation}_{index_version}".replace(
                "-", "_"
            ),
            workspace_id=workspace_id,
            target_store=target_store,
            target_type=target_type,
            target_id=target_id,
            operation=operation,
            index_version=index_version,
            status=IndexJobStatus.QUEUED,
            trace_id=trace_id,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        self._by_identity[key] = record.id
        return IndexJobUpsertResult(record, "inserted")

    def get_by_id(self, index_job_id: str) -> IndexJob:
        return self._records[index_job_id]

    def mark_completed(self, index_job_id: str) -> IndexJob:
        current = self.get_by_id(index_job_id)
        updated = current.model_copy(
            update={
                "status": IndexJobStatus.COMPLETED,
                "completed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[index_job_id] = updated
        return updated

    def mark_failed_retryable(
        self, index_job_id: str, error_code: str, error_message: str
    ) -> IndexJob:
        current = self.get_by_id(index_job_id)
        updated = current.model_copy(
            update={
                "status": IndexJobStatus.FAILED_RETRYABLE,
                "attempt_count": current.attempt_count + 1,
                "last_attempt_at": datetime.now(UTC),
                "last_error_code": error_code,
                "last_error_message": error_message,
                "updated_at": datetime.now(UTC),
            }
        )
        self._records[index_job_id] = updated
        return updated
