from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.contracts.entities import IndexJob
from cortex.contracts.enums import IndexJobStatus
from cortex.db.models import IndexJobRecord


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

    def list_all(self, workspace_id: str | None = None) -> list[IndexJob]:
        return [
            record
            for record in self._records.values()
            if workspace_id is None or record.workspace_id == workspace_id
        ]

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        target_type: str | None = None,
        target_ids: set[str] | None = None,
    ) -> list[IndexJob]:
        return [
            record
            for record in self._records.values()
            if record.workspace_id == workspace_id
            and (target_type is None or record.target_type == target_type)
            and (target_ids is None or record.target_id in target_ids)
        ]

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

    def mark_stale_for_lifecycle(
        self,
        *,
        workspace_id: str,
        target_type: str | None = None,
        target_ids: set[str] | None = None,
    ) -> list[IndexJob]:
        stale: list[IndexJob] = []
        for record in self.list_for_lifecycle(
            workspace_id=workspace_id,
            target_type=target_type,
            target_ids=target_ids,
        ):
            if record.status == IndexJobStatus.STALE:
                continue
            updated = record.model_copy(
                update={
                    "status": IndexJobStatus.STALE,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._records[record.id] = updated
            stale.append(updated)
        return stale


class SqlAlchemyIndexJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(
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
        result = await self.session.execute(
            select(IndexJobRecord).where(
                IndexJobRecord.workspace_id == workspace_id,
                IndexJobRecord.target_store == target_store,
                IndexJobRecord.target_type == target_type,
                IndexJobRecord.target_id == target_id,
                IndexJobRecord.operation == operation,
                IndexJobRecord.index_version == index_version,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return IndexJobUpsertResult(index_job_from_record(existing), "noop")
        now = datetime.now(UTC)
        record = IndexJobRecord(
            id=f"idx_{target_store}_{target_type}_{target_id}_{operation}_{index_version}".replace(
                "-",
                "_",
            ),
            workspace_id=workspace_id,
            target_store=target_store,
            target_type=target_type,
            target_id=target_id,
            operation=operation,
            index_version=index_version,
            status=IndexJobStatus.QUEUED.value,
            trace_id=trace_id,
            attempt_count=0,
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        await self.session.flush()
        return IndexJobUpsertResult(index_job_from_record(record), "inserted")

    async def get_by_id(self, index_job_id: str) -> IndexJob:
        record = await self.session.get(IndexJobRecord, index_job_id)
        if record is None:
            raise KeyError(index_job_id)
        return index_job_from_record(record)

    async def list_all(self, workspace_id: str | None = None) -> list[IndexJob]:
        statement = select(IndexJobRecord)
        if workspace_id is not None:
            statement = statement.where(IndexJobRecord.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return [index_job_from_record(record) for record in result.scalars()]

    async def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        target_type: str | None = None,
        target_ids: set[str] | None = None,
    ) -> list[IndexJob]:
        statement = select(IndexJobRecord).where(
            IndexJobRecord.workspace_id == workspace_id
        )
        if target_type is not None:
            statement = statement.where(IndexJobRecord.target_type == target_type)
        if target_ids is not None:
            statement = statement.where(IndexJobRecord.target_id.in_(target_ids))
        result = await self.session.execute(statement)
        return [index_job_from_record(record) for record in result.scalars()]

    async def mark_completed(self, index_job_id: str) -> IndexJob:
        record = await self.session.get(IndexJobRecord, index_job_id)
        if record is None:
            raise KeyError(index_job_id)
        now = datetime.now(UTC)
        record.status = IndexJobStatus.COMPLETED.value
        record.completed_at = now
        record.updated_at = now
        await self.session.flush()
        return index_job_from_record(record)

    async def mark_failed_retryable(
        self, index_job_id: str, error_code: str, error_message: str
    ) -> IndexJob:
        record = await self.session.get(IndexJobRecord, index_job_id)
        if record is None:
            raise KeyError(index_job_id)
        now = datetime.now(UTC)
        record.status = IndexJobStatus.FAILED_RETRYABLE.value
        record.attempt_count += 1
        record.last_attempt_at = now
        record.last_error_code = error_code
        record.last_error_message = error_message
        record.updated_at = now
        await self.session.flush()
        return index_job_from_record(record)

    async def mark_stale_for_lifecycle(
        self,
        *,
        workspace_id: str,
        target_type: str | None = None,
        target_ids: set[str] | None = None,
    ) -> list[IndexJob]:
        statement = select(IndexJobRecord).where(
            IndexJobRecord.workspace_id == workspace_id
        )
        if target_type is not None:
            statement = statement.where(IndexJobRecord.target_type == target_type)
        if target_ids is not None:
            statement = statement.where(IndexJobRecord.target_id.in_(target_ids))
        result = await self.session.execute(statement)
        stale: list[IndexJob] = []
        now = datetime.now(UTC)
        for record in result.scalars():
            if record.status == IndexJobStatus.STALE.value:
                continue
            record.status = IndexJobStatus.STALE.value
            record.updated_at = now
            stale.append(index_job_from_record(record))
        await self.session.flush()
        return stale


def index_job_from_record(record: IndexJobRecord) -> IndexJob:
    return IndexJob(
        id=record.id,
        workspace_id=record.workspace_id,
        target_store=record.target_store,
        target_type=record.target_type,
        target_id=record.target_id,
        operation=record.operation,
        index_version=record.index_version,
        status=IndexJobStatus(record.status),
        completed_at=record.completed_at,
        trace_id=record.trace_id,
        attempt_count=record.attempt_count,
        last_error_code=record.last_error_code,
        last_error_message=record.last_error_message,
        next_retry_at=record.next_retry_at,
        last_attempt_at=record.last_attempt_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
