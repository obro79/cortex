from __future__ import annotations

import inspect
from collections.abc import Awaitable, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.db.models import (
    DeletionTombstoneRecord,
    ExportJobRecord,
    RetentionPolicyRecord,
)
from cortex.ingestion.payloads import sha256_digest
from cortex.lifecycle.models import (
    DeletionTombstone,
    ExportJob,
    LifecycleActionStatus,
    LifecycleExportResult,
    RetentionPolicy,
    RetentionSweepPlan,
)
from cortex.security.audit import InMemoryAuditLogRepository


class LifecycleLeaseUnavailable(RuntimeError):
    pass


class InMemoryLifecycleRepository:
    def __init__(self) -> None:
        self.retention_policies: dict[str, RetentionPolicy] = {}
        self.deletion_tombstones: dict[str, DeletionTombstone] = {}
        self.export_jobs: dict[str, ExportJob] = {}

    def set_retention_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        updated = replace(policy, updated_at=policy.updated_at or datetime.now(UTC))
        self.retention_policies[policy.workspace_id] = updated
        return updated

    def retention_policy(self, workspace_id: str) -> RetentionPolicy:
        return self.retention_policies.get(
            workspace_id,
            RetentionPolicy(workspace_id=workspace_id),
        )

    def add_deletion_tombstone(self, tombstone: DeletionTombstone) -> DeletionTombstone:
        self.deletion_tombstones[tombstone.id] = tombstone
        return tombstone

    def complete_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        deleted_counts_json: Mapping[str, int],
    ) -> DeletionTombstone:
        tombstone = self.deletion_tombstones[tombstone_id]
        completed = replace(
            tombstone,
            status=LifecycleActionStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            metadata_json={
                **_terminal_metadata(tombstone.metadata_json),
                "deleted_counts_json": dict(deleted_counts_json),
            },
        )
        self.deletion_tombstones[tombstone_id] = completed
        return completed

    def fail_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        error_code: str,
        metadata_json: Mapping[str, object] | None = None,
    ) -> DeletionTombstone:
        tombstone = self.deletion_tombstones[tombstone_id]
        failed = replace(
            tombstone,
            status=LifecycleActionStatus.FAILED,
            metadata_json={
                **_clear_lease_metadata(tombstone.metadata_json),
                "error_code": error_code,
                **dict(metadata_json or {}),
            },
        )
        self.deletion_tombstones[tombstone_id] = failed
        return failed

    def get_deletion_tombstone(self, tombstone_id: str) -> DeletionTombstone:
        return self.deletion_tombstones[tombstone_id]

    def list_tombstones(
        self,
        *,
        workspace_id: str | None = None,
        status: LifecycleActionStatus | None = None,
    ) -> list[DeletionTombstone]:
        return [
            tombstone
            for tombstone in self.deletion_tombstones.values()
            if (workspace_id is None or tombstone.workspace_id == workspace_id)
            and (status is None or tombstone.status == status)
        ]

    def lease_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> DeletionTombstone:
        tombstone = self.deletion_tombstones[tombstone_id]
        if tombstone.status != LifecycleActionStatus.REQUESTED:
            raise LifecycleLeaseUnavailable("deletion_tombstone_not_leaseable")
        leased = replace(
            tombstone,
            status=LifecycleActionStatus.RUNNING,
            metadata_json={
                **tombstone.metadata_json,
                "lease_owner_id": worker_id,
                "lease_expires_at": lease_expires_at.isoformat(),
                "attempt_count": _metadata_int(tombstone.metadata_json, "attempt_count")
                + 1,
            },
        )
        self.deletion_tombstones[tombstone_id] = leased
        return leased

    def retry_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        error_code: str,
    ) -> DeletionTombstone:
        tombstone = self.deletion_tombstones[tombstone_id]
        retried = replace(
            tombstone,
            status=LifecycleActionStatus.REQUESTED,
            metadata_json={
                **_clear_lease_metadata(tombstone.metadata_json),
                "last_error_code": error_code,
            },
        )
        self.deletion_tombstones[tombstone_id] = retried
        return retried

    def add_export_job(self, job: ExportJob) -> ExportJob:
        self.export_jobs[job.id] = job
        return job

    def complete_export_job(
        self,
        *,
        job_id: str,
        destination_ref: str,
        metadata_json: Mapping[str, object] | None = None,
    ) -> ExportJob:
        job = self.export_jobs[job_id]
        completed = replace(
            job,
            status=LifecycleActionStatus.COMPLETED,
            destination_ref=destination_ref,
            completed_at=datetime.now(UTC),
            metadata_json={
                **_terminal_metadata(job.metadata_json),
                **dict(metadata_json or {}),
            },
        )
        self.export_jobs[job_id] = completed
        return completed

    def fail_export_job(self, *, job_id: str, error_code: str) -> ExportJob:
        job = self.export_jobs[job_id]
        failed = replace(
            job,
            status=LifecycleActionStatus.FAILED,
            metadata_json={
                **_clear_lease_metadata(job.metadata_json),
                "error_code": error_code,
            },
        )
        self.export_jobs[job_id] = failed
        return failed

    def get_export_job(self, job_id: str) -> ExportJob:
        return self.export_jobs[job_id]

    def list_export_jobs(
        self,
        *,
        workspace_id: str | None = None,
        status: LifecycleActionStatus | None = None,
    ) -> list[ExportJob]:
        return [
            job
            for job in self.export_jobs.values()
            if (workspace_id is None or job.workspace_id == workspace_id)
            and (status is None or job.status == status)
        ]

    def lease_export_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> ExportJob:
        job = self.export_jobs[job_id]
        if job.status != LifecycleActionStatus.REQUESTED:
            raise LifecycleLeaseUnavailable("export_job_not_leaseable")
        leased = replace(
            job,
            status=LifecycleActionStatus.RUNNING,
            metadata_json={
                **job.metadata_json,
                "lease_owner_id": worker_id,
                "lease_expires_at": lease_expires_at.isoformat(),
                "attempt_count": _metadata_int(job.metadata_json, "attempt_count") + 1,
            },
        )
        self.export_jobs[job_id] = leased
        return leased

    def retry_export_job(self, *, job_id: str, error_code: str) -> ExportJob:
        job = self.export_jobs[job_id]
        retried = replace(
            job,
            status=LifecycleActionStatus.REQUESTED,
            metadata_json={
                **_clear_lease_metadata(job.metadata_json),
                "last_error_code": error_code,
            },
        )
        self.export_jobs[job_id] = retried
        return retried


def retention_policy_from_record(record: RetentionPolicyRecord) -> RetentionPolicy:
    return RetentionPolicy(
        workspace_id=record.workspace_id,
        raw_event_days=record.raw_event_days,
        payload_days=record.payload_days,
        audit_log_days=record.audit_log_days,
        tombstone_days=record.tombstone_days,
        updated_at=record.updated_at,
    )


def deletion_tombstone_from_record(
    record: DeletionTombstoneRecord,
) -> DeletionTombstone:
    return DeletionTombstone(
        id=record.id,
        workspace_id=record.workspace_id,
        target_type=record.target_type,
        target_id_hash=record.target_id_hash,
        status=LifecycleActionStatus(record.status),
        requested_by_user_id=record.requested_by_user_id,
        reason=record.reason,
        created_at=record.created_at,
        completed_at=record.completed_at,
        metadata_json=dict(record.metadata_json),
    )


def export_job_from_record(record: ExportJobRecord) -> ExportJob:
    return ExportJob(
        id=record.id,
        workspace_id=record.workspace_id,
        requested_by_user_id=record.requested_by_user_id,
        status=LifecycleActionStatus(record.status),
        export_scope=record.export_scope,
        destination_ref=record.destination_ref,
        created_at=record.created_at,
        completed_at=record.completed_at,
        metadata_json=dict(record.metadata_json),
    )


class SqlAlchemyLifecycleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def set_retention_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        now = datetime.now(UTC)
        record = await self.session.get(RetentionPolicyRecord, policy.workspace_id)
        if record is None:
            record = RetentionPolicyRecord(
                workspace_id=policy.workspace_id,
                raw_event_days=policy.raw_event_days,
                payload_days=policy.payload_days,
                audit_log_days=policy.audit_log_days,
                tombstone_days=policy.tombstone_days,
                updated_at=policy.updated_at or now,
            )
            self.session.add(record)
        else:
            record.raw_event_days = policy.raw_event_days
            record.payload_days = policy.payload_days
            record.audit_log_days = policy.audit_log_days
            record.tombstone_days = policy.tombstone_days
            record.updated_at = policy.updated_at or now
        await self.session.flush()
        return retention_policy_from_record(record)

    async def retention_policy(self, workspace_id: str) -> RetentionPolicy:
        record = await self.session.get(RetentionPolicyRecord, workspace_id)
        if record is None:
            return RetentionPolicy(workspace_id=workspace_id)
        return retention_policy_from_record(record)

    async def add_deletion_tombstone(
        self, tombstone: DeletionTombstone
    ) -> DeletionTombstone:
        record = DeletionTombstoneRecord(
            id=tombstone.id,
            workspace_id=tombstone.workspace_id,
            target_type=tombstone.target_type,
            target_id_hash=tombstone.target_id_hash,
            status=LifecycleActionStatus(tombstone.status).value,
            requested_by_user_id=tombstone.requested_by_user_id,
            reason=tombstone.reason,
            metadata_json=dict(tombstone.metadata_json),
            created_at=tombstone.created_at,
            completed_at=tombstone.completed_at,
        )
        self.session.add(record)
        await self.session.flush()
        return tombstone

    async def complete_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        deleted_counts_json: Mapping[str, int],
    ) -> DeletionTombstone:
        record = await self._deletion_tombstone_record(tombstone_id)
        record.status = LifecycleActionStatus.COMPLETED.value
        record.completed_at = datetime.now(UTC)
        record.metadata_json = {
            **_terminal_metadata(record.metadata_json),
            "deleted_counts_json": dict(deleted_counts_json),
        }
        await self.session.flush()
        return deletion_tombstone_from_record(record)

    async def fail_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        error_code: str,
        metadata_json: Mapping[str, object] | None = None,
    ) -> DeletionTombstone:
        record = await self._deletion_tombstone_record(tombstone_id)
        record.status = LifecycleActionStatus.FAILED.value
        record.metadata_json = {
            **_clear_lease_metadata(record.metadata_json),
            "error_code": error_code,
            **dict(metadata_json or {}),
        }
        await self.session.flush()
        return deletion_tombstone_from_record(record)

    async def get_deletion_tombstone(self, tombstone_id: str) -> DeletionTombstone:
        return deletion_tombstone_from_record(
            await self._deletion_tombstone_record(tombstone_id)
        )

    async def add_export_job(self, job: ExportJob) -> ExportJob:
        record = ExportJobRecord(
            id=job.id,
            workspace_id=job.workspace_id,
            requested_by_user_id=job.requested_by_user_id,
            status=LifecycleActionStatus(job.status).value,
            export_scope=job.export_scope,
            destination_ref=job.destination_ref,
            metadata_json=dict(job.metadata_json),
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        self.session.add(record)
        await self.session.flush()
        return job

    async def complete_export_job(
        self,
        *,
        job_id: str,
        destination_ref: str,
        metadata_json: Mapping[str, object] | None = None,
    ) -> ExportJob:
        record = await self._export_job_record(job_id)
        record.status = LifecycleActionStatus.COMPLETED.value
        record.destination_ref = destination_ref
        record.completed_at = datetime.now(UTC)
        record.metadata_json = {
            **_terminal_metadata(record.metadata_json),
            **dict(metadata_json or {}),
        }
        await self.session.flush()
        return export_job_from_record(record)

    async def fail_export_job(self, *, job_id: str, error_code: str) -> ExportJob:
        record = await self._export_job_record(job_id)
        record.status = LifecycleActionStatus.FAILED.value
        record.metadata_json = {
            **_clear_lease_metadata(record.metadata_json),
            "error_code": error_code,
        }
        await self.session.flush()
        return export_job_from_record(record)

    async def get_export_job(self, job_id: str) -> ExportJob:
        return export_job_from_record(await self._export_job_record(job_id))

    async def list_tombstones(
        self,
        *,
        workspace_id: str | None = None,
        status: LifecycleActionStatus | None = None,
    ) -> list[DeletionTombstone]:
        statement = select(DeletionTombstoneRecord)
        if workspace_id is not None:
            statement = statement.where(
                DeletionTombstoneRecord.workspace_id == workspace_id
            )
        if status is not None:
            statement = statement.where(
                DeletionTombstoneRecord.status == LifecycleActionStatus(status).value
            )
        result = await self.session.execute(statement)
        return [deletion_tombstone_from_record(record) for record in result.scalars()]

    async def lease_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> DeletionTombstone:
        record = await self._deletion_tombstone_record_for_update(tombstone_id)
        if record.status != LifecycleActionStatus.REQUESTED.value:
            raise LifecycleLeaseUnavailable("deletion_tombstone_not_leaseable")
        record.status = LifecycleActionStatus.RUNNING.value
        record.metadata_json = {
            **record.metadata_json,
            "lease_owner_id": worker_id,
            "lease_expires_at": lease_expires_at.isoformat(),
            "attempt_count": _metadata_int(record.metadata_json, "attempt_count") + 1,
        }
        await self.session.flush()
        return deletion_tombstone_from_record(record)

    async def retry_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        error_code: str,
    ) -> DeletionTombstone:
        record = await self._deletion_tombstone_record(tombstone_id)
        record.status = LifecycleActionStatus.REQUESTED.value
        record.metadata_json = {
            **_clear_lease_metadata(record.metadata_json),
            "last_error_code": error_code,
        }
        await self.session.flush()
        return deletion_tombstone_from_record(record)

    async def list_export_jobs(
        self,
        *,
        workspace_id: str | None = None,
        status: LifecycleActionStatus | None = None,
    ) -> list[ExportJob]:
        statement = select(ExportJobRecord)
        if workspace_id is not None:
            statement = statement.where(ExportJobRecord.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(
                ExportJobRecord.status == LifecycleActionStatus(status).value
            )
        result = await self.session.execute(statement)
        return [export_job_from_record(record) for record in result.scalars()]

    async def lease_export_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> ExportJob:
        record = await self._export_job_record_for_update(job_id)
        if record.status != LifecycleActionStatus.REQUESTED.value:
            raise LifecycleLeaseUnavailable("export_job_not_leaseable")
        record.status = LifecycleActionStatus.RUNNING.value
        record.metadata_json = {
            **record.metadata_json,
            "lease_owner_id": worker_id,
            "lease_expires_at": lease_expires_at.isoformat(),
            "attempt_count": _metadata_int(record.metadata_json, "attempt_count") + 1,
        }
        await self.session.flush()
        return export_job_from_record(record)

    async def retry_export_job(self, *, job_id: str, error_code: str) -> ExportJob:
        record = await self._export_job_record(job_id)
        record.status = LifecycleActionStatus.REQUESTED.value
        record.metadata_json = {
            **_clear_lease_metadata(record.metadata_json),
            "last_error_code": error_code,
        }
        await self.session.flush()
        return export_job_from_record(record)

    async def _deletion_tombstone_record(
        self, tombstone_id: str
    ) -> DeletionTombstoneRecord:
        record = await self.session.get(DeletionTombstoneRecord, tombstone_id)
        if record is None:
            raise KeyError(tombstone_id)
        return record

    async def _deletion_tombstone_record_for_update(
        self, tombstone_id: str
    ) -> DeletionTombstoneRecord:
        result = await self.session.execute(
            select(DeletionTombstoneRecord)
            .where(DeletionTombstoneRecord.id == tombstone_id)
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise KeyError(tombstone_id)
        return record

    async def _export_job_record(self, job_id: str) -> ExportJobRecord:
        record = await self.session.get(ExportJobRecord, job_id)
        if record is None:
            raise KeyError(job_id)
        return record

    async def _export_job_record_for_update(self, job_id: str) -> ExportJobRecord:
        result = await self.session.execute(
            select(ExportJobRecord)
            .where(ExportJobRecord.id == job_id)
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise KeyError(job_id)
        return record


class LifecycleRepository(Protocol):
    def set_retention_policy(
        self, policy: RetentionPolicy
    ) -> RetentionPolicy | Awaitable[RetentionPolicy]: ...

    def retention_policy(
        self, workspace_id: str
    ) -> RetentionPolicy | Awaitable[RetentionPolicy]: ...

    def add_deletion_tombstone(
        self, tombstone: DeletionTombstone
    ) -> DeletionTombstone | Awaitable[DeletionTombstone]: ...

    def complete_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        deleted_counts_json: Mapping[str, int],
    ) -> DeletionTombstone | Awaitable[DeletionTombstone]: ...

    def fail_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        error_code: str,
        metadata_json: Mapping[str, object] | None = None,
    ) -> DeletionTombstone | Awaitable[DeletionTombstone]: ...

    def add_export_job(self, job: ExportJob) -> ExportJob | Awaitable[ExportJob]: ...

    def complete_export_job(
        self,
        *,
        job_id: str,
        destination_ref: str,
        metadata_json: Mapping[str, object] | None = None,
    ) -> ExportJob | Awaitable[ExportJob]: ...

    def fail_export_job(
        self, *, job_id: str, error_code: str
    ) -> ExportJob | Awaitable[ExportJob]: ...

    def get_deletion_tombstone(
        self, tombstone_id: str
    ) -> DeletionTombstone | Awaitable[DeletionTombstone]: ...

    def list_tombstones(
        self,
        *,
        workspace_id: str | None = None,
        status: LifecycleActionStatus | None = None,
    ) -> list[DeletionTombstone] | Awaitable[list[DeletionTombstone]]: ...

    def lease_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> DeletionTombstone | Awaitable[DeletionTombstone]: ...

    def retry_deletion_tombstone(
        self,
        *,
        tombstone_id: str,
        error_code: str,
    ) -> DeletionTombstone | Awaitable[DeletionTombstone]: ...

    def get_export_job(self, job_id: str) -> ExportJob | Awaitable[ExportJob]: ...

    def list_export_jobs(
        self,
        *,
        workspace_id: str | None = None,
        status: LifecycleActionStatus | None = None,
    ) -> list[ExportJob] | Awaitable[list[ExportJob]]: ...

    def lease_export_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> ExportJob | Awaitable[ExportJob]: ...

    def retry_export_job(
        self, *, job_id: str, error_code: str
    ) -> ExportJob | Awaitable[ExportJob]: ...


class LifecycleDeletionExecutor(Protocol):
    def delete(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
    ) -> Mapping[str, int] | Awaitable[Mapping[str, int]]: ...


class LifecycleExportExecutor(Protocol):
    def export(
        self,
        *,
        workspace_id: str,
        export_scope: str,
    ) -> LifecycleExportResult | Awaitable[LifecycleExportResult]: ...


class LifecycleDeletionIntegrityError(RuntimeError):
    def __init__(self, mismatches: Mapping[str, object]) -> None:
        super().__init__("lifecycle deletion cleanup mismatch")
        self.error_code = "cleanup_mismatch"
        self.mismatches = dict(mismatches)


class LifecycleService:
    def __init__(
        self,
        repository: LifecycleRepository,
        *,
        audit_log: InMemoryAuditLogRepository | None = None,
    ) -> None:
        self.repository = repository
        self.audit_log = audit_log or InMemoryAuditLogRepository()

    async def configure_retention(
        self,
        *,
        policy: RetentionPolicy,
        actor_id: str,
    ) -> RetentionPolicy:
        saved = await _resolve(self.repository.set_retention_policy(policy))
        self.audit_log.append(
            workspace_id=policy.workspace_id,
            actor_id=actor_id,
            action="lifecycle.retention.configure",
            target_type="retention_policy",
            target_id=policy.workspace_id,
            decision="allowed",
            metadata_json={
                "raw_event_days": policy.raw_event_days,
                "payload_days": policy.payload_days,
                "audit_log_days": policy.audit_log_days,
                "tombstone_days": policy.tombstone_days,
            },
        )
        return saved

    async def plan_retention_sweep(
        self, *, workspace_id: str, now: datetime | None = None
    ) -> RetentionSweepPlan:
        policy = await _resolve(self.repository.retention_policy(workspace_id))
        reference = now or datetime.now(UTC)
        return RetentionSweepPlan(
            workspace_id=workspace_id,
            raw_events_before=_cutoff(reference, policy.raw_event_days),
            payloads_before=_cutoff(reference, policy.payload_days),
            audit_logs_before=_cutoff(reference, policy.audit_log_days),
            tombstones_before=_cutoff(reference, policy.tombstone_days),
        )

    async def request_deletion(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
        requested_by_user_id: str,
        reason: str,
        queue_execution: bool = False,
    ) -> DeletionTombstone:
        now = datetime.now(UTC)
        target_id_hash = sha256_digest(target_id.encode())
        tombstone = DeletionTombstone(
            id=_stable_id("del", workspace_id, target_type, target_id_hash),
            workspace_id=workspace_id,
            target_type=target_type,
            target_id_hash=target_id_hash,
            status=LifecycleActionStatus.REQUESTED,
            requested_by_user_id=requested_by_user_id,
            reason=reason,
            created_at=now,
            metadata_json={"target_id_ref": target_id} if queue_execution else {},
        )
        saved = await _resolve(self.repository.add_deletion_tombstone(tombstone))
        self.audit_log.append(
            workspace_id=workspace_id,
            actor_id=requested_by_user_id,
            action="lifecycle.deletion.request",
            target_type=target_type,
            target_id=target_id,
            decision="allowed",
            reason=reason,
        )
        return saved

    async def execute_deletion(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
        requested_by_user_id: str,
        reason: str,
        executor: LifecycleDeletionExecutor,
    ) -> DeletionTombstone:
        tombstone = await self.request_deletion(
            workspace_id=workspace_id,
            target_type=target_type,
            target_id=target_id,
            requested_by_user_id=requested_by_user_id,
            reason=reason,
        )
        return await self.execute_deletion_tombstone(
            tombstone=tombstone,
            target_id=target_id,
            executor=executor,
        )

    async def execute_deletion_tombstone(
        self,
        *,
        tombstone: DeletionTombstone,
        target_id: str,
        executor: LifecycleDeletionExecutor,
    ) -> DeletionTombstone:
        counts: Mapping[str, int] = {}
        try:
            counts = await _resolve(
                executor.delete(
                    workspace_id=tombstone.workspace_id,
                    target_type=tombstone.target_type,
                    target_id=target_id,
                )
            )
            _validate_deletion_counts(counts)
        except LifecycleDeletionIntegrityError as error:
            failed = await _resolve(
                self.repository.fail_deletion_tombstone(
                    tombstone_id=tombstone.id,
                    error_code=error.error_code,
                    metadata_json={
                        "deleted_counts_json": dict(counts),
                        "mismatches_json": error.mismatches,
                    },
                )
            )
            self.audit_log.append(
                workspace_id=tombstone.workspace_id,
                actor_id=tombstone.requested_by_user_id,
                action="lifecycle.deletion.failed",
                target_type=tombstone.target_type,
                target_id=target_id,
                decision="allowed",
                reason=error.error_code,
                metadata_json={"mismatches_json": error.mismatches},
            )
            return failed
        except Exception:
            await _resolve(
                self.repository.fail_deletion_tombstone(
                    tombstone_id=tombstone.id,
                    error_code="executor_failed",
                )
            )
            self.audit_log.append(
                workspace_id=tombstone.workspace_id,
                actor_id=tombstone.requested_by_user_id,
                action="lifecycle.deletion.failed",
                target_type=tombstone.target_type,
                target_id=target_id,
                decision="allowed",
                reason="executor_failed",
            )
            raise
        completed = await _resolve(
            self.repository.complete_deletion_tombstone(
                tombstone_id=tombstone.id,
                deleted_counts_json=counts,
            )
        )
        self.audit_log.append(
            workspace_id=tombstone.workspace_id,
            actor_id=tombstone.requested_by_user_id,
            action="lifecycle.deletion.complete",
            target_type=tombstone.target_type,
            target_id=target_id,
            decision="allowed",
            metadata_json={"deleted_counts_json": dict(counts)},
        )
        return completed

    async def request_export(
        self,
        *,
        workspace_id: str,
        requested_by_user_id: str,
        export_scope: str,
    ) -> ExportJob:
        now = datetime.now(UTC)
        job = ExportJob(
            id=_stable_id(
                "export",
                workspace_id,
                requested_by_user_id,
                now.isoformat(),
            ),
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
            status=LifecycleActionStatus.REQUESTED,
            export_scope=export_scope,
            destination_ref=None,
            created_at=now,
        )
        saved = await _resolve(self.repository.add_export_job(job))
        self.audit_log.append(
            workspace_id=workspace_id,
            actor_id=requested_by_user_id,
            action="lifecycle.export.request",
            target_type="export_job",
            target_id=job.id,
            decision="allowed",
            metadata_json={"export_scope": export_scope},
        )
        return saved

    async def execute_export(
        self,
        *,
        workspace_id: str,
        requested_by_user_id: str,
        export_scope: str,
        executor: LifecycleExportExecutor,
    ) -> ExportJob:
        job = await self.request_export(
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
            export_scope=export_scope,
        )
        return await self.execute_export_job(job=job, executor=executor)

    async def execute_export_job(
        self,
        *,
        job: ExportJob,
        executor: LifecycleExportExecutor,
    ) -> ExportJob:
        try:
            result = await _resolve(
                executor.export(
                    workspace_id=job.workspace_id,
                    export_scope=job.export_scope,
                )
            )
        except Exception:
            await _resolve(
                self.repository.fail_export_job(
                    job_id=job.id,
                    error_code="executor_failed",
                )
            )
            self.audit_log.append(
                workspace_id=job.workspace_id,
                actor_id=job.requested_by_user_id,
                action="lifecycle.export.failed",
                target_type="export_job",
                target_id=job.id,
                decision="allowed",
                reason="executor_failed",
            )
            raise
        completed = await _resolve(
            self.repository.complete_export_job(
                job_id=job.id,
                destination_ref=result.destination_ref,
                metadata_json=result.metadata_json,
            )
        )
        self.audit_log.append(
            workspace_id=job.workspace_id,
            actor_id=job.requested_by_user_id,
            action="lifecycle.export.complete",
            target_type="export_job",
            target_id=job.id,
            decision="allowed",
            metadata_json={
                "export_scope": job.export_scope,
                "destination_ref": result.destination_ref,
                **result.metadata_json,
            },
        )
        return completed


async def _resolve[T](value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await cast(Awaitable[T], value)
    return value


def _validate_deletion_counts(counts: Mapping[str, int]) -> None:
    mismatches: dict[str, object] = {}
    for actual_key, expected_key in (
        ("raw_events", "expected_raw_events"),
        ("source_objects", "expected_source_objects"),
        ("source_files", "expected_source_files"),
        ("source_chunks", "expected_source_chunks"),
        ("embeddings", "expected_embeddings"),
        ("index_jobs", "expected_index_jobs"),
        ("vector_points", "expected_vector_points"),
        ("payload_refs_deleted", "expected_payload_refs"),
    ):
        if expected_key not in counts:
            continue
        expected = counts[expected_key]
        actual = counts.get(actual_key, 0)
        if actual != expected:
            mismatches[actual_key] = {"expected": expected, "actual": actual}
    skipped_payloads = counts.get("payload_refs_skipped", 0)
    if skipped_payloads:
        mismatches["payload_refs_skipped"] = {
            "expected": 0,
            "actual": skipped_payloads,
        }
    if mismatches:
        raise LifecycleDeletionIntegrityError(mismatches)


def _clear_lease_metadata(metadata_json: Mapping[str, object]) -> dict[str, object]:
    metadata = dict(metadata_json)
    metadata.pop("lease_owner_id", None)
    metadata.pop("lease_expires_at", None)
    return metadata


def _terminal_metadata(metadata_json: Mapping[str, object]) -> dict[str, object]:
    metadata = _clear_lease_metadata(metadata_json)
    metadata.pop("target_id_ref", None)
    return metadata


def _metadata_int(metadata_json: Mapping[str, object], key: str) -> int:
    value = metadata_json.get(key, 0)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _cutoff(reference: datetime, days: int | None) -> datetime | None:
    if days is None:
        return None
    return reference - timedelta(days=days)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256_digest(":".join(parts).encode()).removeprefix("sha256:")[:24]
    return f"{prefix}_{digest}"
