from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from cortex.ingestion.payloads import sha256_digest
from cortex.lifecycle.models import (
    DeletionTombstone,
    ExportJob,
    LifecycleActionStatus,
    RetentionPolicy,
    RetentionSweepPlan,
)
from cortex.security.audit import InMemoryAuditLogRepository


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

    def add_deletion_tombstone(
        self, tombstone: DeletionTombstone
    ) -> DeletionTombstone:
        self.deletion_tombstones[tombstone.id] = tombstone
        return tombstone

    def add_export_job(self, job: ExportJob) -> ExportJob:
        self.export_jobs[job.id] = job
        return job

    def complete_export_job(
        self, *, job_id: str, destination_ref: str
    ) -> ExportJob:
        job = self.export_jobs[job_id]
        completed = replace(
            job,
            status=LifecycleActionStatus.COMPLETED,
            destination_ref=destination_ref,
            completed_at=datetime.now(UTC),
        )
        self.export_jobs[job_id] = completed
        return completed


class LifecycleService:
    def __init__(
        self,
        repository: InMemoryLifecycleRepository,
        *,
        audit_log: InMemoryAuditLogRepository | None = None,
    ) -> None:
        self.repository = repository
        self.audit_log = audit_log or InMemoryAuditLogRepository()

    def configure_retention(
        self,
        *,
        policy: RetentionPolicy,
        actor_id: str,
    ) -> RetentionPolicy:
        saved = self.repository.set_retention_policy(policy)
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

    def plan_retention_sweep(
        self, *, workspace_id: str, now: datetime | None = None
    ) -> RetentionSweepPlan:
        policy = self.repository.retention_policy(workspace_id)
        reference = now or datetime.now(UTC)
        return RetentionSweepPlan(
            workspace_id=workspace_id,
            raw_events_before=_cutoff(reference, policy.raw_event_days),
            payloads_before=_cutoff(reference, policy.payload_days),
            audit_logs_before=_cutoff(reference, policy.audit_log_days),
            tombstones_before=_cutoff(reference, policy.tombstone_days),
        )

    def request_deletion(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
        requested_by_user_id: str,
        reason: str,
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
        )
        saved = self.repository.add_deletion_tombstone(tombstone)
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

    def request_export(
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
        saved = self.repository.add_export_job(job)
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


def _cutoff(reference: datetime, days: int | None) -> datetime | None:
    if days is None:
        return None
    return reference - timedelta(days=days)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256_digest(":".join(parts).encode()).removeprefix("sha256:")[:24]
    return f"{prefix}_{digest}"
