from datetime import UTC, datetime

from cortex.lifecycle import (
    InMemoryLifecycleRepository,
    LifecycleActionStatus,
    LifecycleService,
    RetentionPolicy,
)
from cortex.security.audit import InMemoryAuditLogRepository


def test_retention_policy_builds_sweep_plan_and_audits_config() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = LifecycleService(InMemoryLifecycleRepository(), audit_log=audit_log)

    policy = service.configure_retention(
        policy=RetentionPolicy(
            workspace_id="ws_1",
            raw_event_days=30,
            payload_days=7,
            audit_log_days=None,
            tombstone_days=365,
        ),
        actor_id="usr_1",
    )
    plan = service.plan_retention_sweep(
        workspace_id="ws_1",
        now=datetime(2026, 5, 14, tzinfo=UTC),
    )

    assert policy.updated_at is not None
    assert plan.raw_events_before == datetime(2026, 4, 14, tzinfo=UTC)
    assert plan.payloads_before == datetime(2026, 5, 7, tzinfo=UTC)
    assert plan.audit_logs_before is None
    assert audit_log.list_for_workspace("ws_1")[0].action == (
        "lifecycle.retention.configure"
    )


def test_deletion_request_creates_hashed_tombstone_and_audit() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = LifecycleService(InMemoryLifecycleRepository(), audit_log=audit_log)

    tombstone = service.request_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_secret",
        requested_by_user_id="usr_1",
        reason="customer_request",
    )

    record = audit_log.list_for_workspace("ws_1")[0]
    assert tombstone.status == LifecycleActionStatus.REQUESTED
    assert tombstone.target_id_hash.startswith("sha256:")
    assert tombstone.target_id_hash != "src_secret"
    assert record.target_id_hash is not None
    assert record.reason == "customer_request"


def test_export_job_lifecycle() -> None:
    repo = InMemoryLifecycleRepository()
    service = LifecycleService(repo)

    job = service.request_export(
        workspace_id="ws_1",
        requested_by_user_id="usr_1",
        export_scope="workspace",
    )
    completed = repo.complete_export_job(
        job_id=job.id,
        destination_ref="s3://exports/ws_1/export.jsonl",
    )

    assert job.status == LifecycleActionStatus.REQUESTED
    assert completed.status == LifecycleActionStatus.COMPLETED
    assert completed.destination_ref == "s3://exports/ws_1/export.jsonl"
