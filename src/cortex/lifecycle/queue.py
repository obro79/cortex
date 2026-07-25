from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cortex.lifecycle.models import (
    DeletionTombstone,
    ExportJob,
    LifecycleActionStatus,
)
from cortex.lifecycle.service import (
    LifecycleDeletionExecutor,
    LifecycleExportExecutor,
    LifecycleLeaseUnavailable,
    LifecycleService,
)
from cortex.utils.asyncio import maybe_await


@dataclass(frozen=True)
class LifecycleQueueRunResult:
    deletions_processed: int = 0
    exports_processed: int = 0
    leases_acquired: int = 0
    retries_scheduled: int = 0
    failures: int = 0


class LifecycleQueueWorker:
    def __init__(
        self,
        *,
        service: LifecycleService,
        deletion_executor: LifecycleDeletionExecutor,
        export_executor: LifecycleExportExecutor,
        worker_id: str,
        lease_seconds: int = 300,
        max_attempts: int = 3,
        batch_size: int = 10,
    ) -> None:
        self.service = service
        self.repository = service.repository
        self.deletion_executor = deletion_executor
        self.export_executor = export_executor
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self.batch_size = batch_size

    async def process_once(
        self, *, now: datetime | None = None
    ) -> LifecycleQueueRunResult:
        reference = now or datetime.now(UTC)
        retried_stale = await self._retry_stale_leases(reference)
        deletion_counts = await self._process_deletions(reference)
        export_counts = await self._process_exports(reference)
        return LifecycleQueueRunResult(
            deletions_processed=deletion_counts.processed,
            exports_processed=export_counts.processed,
            leases_acquired=deletion_counts.leased + export_counts.leased,
            retries_scheduled=(
                retried_stale
                + deletion_counts.retries_scheduled
                + export_counts.retries_scheduled
            ),
            failures=deletion_counts.failures + export_counts.failures,
        )

    async def _retry_stale_leases(self, now: datetime) -> int:
        retried = 0
        running_tombstones = await maybe_await(
            self.repository.list_tombstones(status=LifecycleActionStatus.RUNNING)
        )
        for tombstone in running_tombstones:
            if _lease_expired(tombstone.metadata_json, now):
                await maybe_await(
                    self.repository.retry_deletion_tombstone(
                        tombstone_id=tombstone.id,
                        error_code="lease_expired",
                    )
                )
                retried += 1
        running_jobs = await maybe_await(
            self.repository.list_export_jobs(status=LifecycleActionStatus.RUNNING)
        )
        for job in running_jobs:
            if _lease_expired(job.metadata_json, now):
                await maybe_await(
                    self.repository.retry_export_job(
                        job_id=job.id,
                        error_code="lease_expired",
                    )
                )
                retried += 1
        return retried

    async def _process_deletions(self, now: datetime) -> _ProcessingCounts:
        counts = _ProcessingCounts()
        tombstones = await maybe_await(
            self.repository.list_tombstones(status=LifecycleActionStatus.REQUESTED)
        )
        for tombstone in tombstones[: self.batch_size]:
            try:
                leased = await maybe_await(
                    self.repository.lease_deletion_tombstone(
                        tombstone_id=tombstone.id,
                        worker_id=self.worker_id,
                        lease_expires_at=now + timedelta(seconds=self.lease_seconds),
                    )
                )
            except LifecycleLeaseUnavailable:
                continue
            counts.leased += 1
            target_id = leased.metadata_json.get("target_id_ref")
            if not isinstance(target_id, str) or not target_id:
                await maybe_await(
                    self.repository.fail_deletion_tombstone(
                        tombstone_id=leased.id,
                        error_code="missing_target_ref",
                    )
                )
                counts.failures += 1
                continue
            try:
                result = await self.service.execute_deletion_tombstone(
                    tombstone=leased,
                    target_id=target_id,
                    executor=self.deletion_executor,
                )
            except Exception:
                counts.failures += 1
                if _attempt_count(leased) < self.max_attempts:
                    await maybe_await(
                        self.repository.retry_deletion_tombstone(
                            tombstone_id=leased.id,
                            error_code="executor_failed",
                        )
                    )
                    counts.retries_scheduled += 1
                continue
            counts.processed += 1
            if result.status == LifecycleActionStatus.FAILED:
                counts.failures += 1
                if _attempt_count(leased) < self.max_attempts:
                    await maybe_await(
                        self.repository.retry_deletion_tombstone(
                            tombstone_id=leased.id,
                            error_code=str(
                                result.metadata_json.get(
                                    "error_code", "execution_failed"
                                )
                            ),
                        )
                    )
                    counts.retries_scheduled += 1
        return counts

    async def _process_exports(self, now: datetime) -> _ProcessingCounts:
        counts = _ProcessingCounts()
        jobs = await maybe_await(
            self.repository.list_export_jobs(status=LifecycleActionStatus.REQUESTED)
        )
        for job in jobs[: self.batch_size]:
            try:
                leased = await maybe_await(
                    self.repository.lease_export_job(
                        job_id=job.id,
                        worker_id=self.worker_id,
                        lease_expires_at=now + timedelta(seconds=self.lease_seconds),
                    )
                )
            except LifecycleLeaseUnavailable:
                continue
            counts.leased += 1
            try:
                await self.service.execute_export_job(
                    job=leased,
                    executor=self.export_executor,
                )
            except Exception:
                counts.failures += 1
                if _attempt_count(leased) < self.max_attempts:
                    await maybe_await(
                        self.repository.retry_export_job(
                            job_id=leased.id,
                            error_code="executor_failed",
                        )
                    )
                    counts.retries_scheduled += 1
                continue
            counts.processed += 1
        return counts


@dataclass
class _ProcessingCounts:
    processed: int = 0
    leased: int = 0
    retries_scheduled: int = 0
    failures: int = 0


def _attempt_count(record: DeletionTombstone | ExportJob) -> int:
    value = record.metadata_json.get("attempt_count", 0)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _lease_expired(metadata_json: dict[str, object], now: datetime) -> bool:
    value = metadata_json.get("lease_expires_at")
    if not isinstance(value, str) or not value:
        return False
    try:
        expires_at = datetime.fromisoformat(value)
    except ValueError:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now
