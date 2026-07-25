from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cortex.lifecycle import (
    InMemoryLifecycleRepository,
    LifecycleActionStatus,
    LifecycleExportResult,
    LifecycleLeaseUnavailable,
    LifecycleQueueWorker,
    LifecycleService,
)


class RecordingDeletionExecutor:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, str]] = []

    def delete(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
    ) -> dict[str, int]:
        self.calls.append(
            {
                "workspace_id": workspace_id,
                "target_type": target_type,
                "target_id": target_id,
            }
        )
        if self.fail:
            raise RuntimeError("delete failed")
        return {"raw_events": 1}


class RecordingExportExecutor:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, str]] = []

    def export(
        self,
        *,
        workspace_id: str,
        export_scope: str,
    ) -> LifecycleExportResult:
        self.calls.append(
            {
                "workspace_id": workspace_id,
                "export_scope": export_scope,
            }
        )
        if self.fail:
            raise RuntimeError("export failed")
        return LifecycleExportResult(
            destination_ref=f"payload://exports/{workspace_id}.jsonl",
            metadata_json={"counts": {"raw_events": 1}},
        )


@pytest.mark.asyncio
async def test_lifecycle_queue_leases_and_executes_deletion_and_export() -> None:
    repository = InMemoryLifecycleRepository()
    service = LifecycleService(repository)
    deletion_executor = RecordingDeletionExecutor()
    export_executor = RecordingExportExecutor()
    tombstone = await service.request_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_1",
        requested_by_user_id="usr_1",
        reason="customer_request",
        queue_execution=True,
    )
    job = await service.request_export(
        workspace_id="ws_1",
        requested_by_user_id="usr_1",
        export_scope="workspace",
    )
    worker = LifecycleQueueWorker(
        service=service,
        deletion_executor=deletion_executor,
        export_executor=export_executor,
        worker_id="worker_1",
    )

    result = await worker.process_once(now=datetime(2026, 5, 14, tzinfo=UTC))

    assert result.deletions_processed == 1
    assert result.exports_processed == 1
    assert result.leases_acquired == 2
    assert deletion_executor.calls == [
        {
            "workspace_id": "ws_1",
            "target_type": "source_connection",
            "target_id": "src_1",
        }
    ]
    assert export_executor.calls == [
        {
            "workspace_id": "ws_1",
            "export_scope": "workspace",
        }
    ]
    completed_tombstone = repository.get_deletion_tombstone(tombstone.id)
    completed_job = repository.get_export_job(job.id)
    assert completed_tombstone.status == LifecycleActionStatus.COMPLETED
    assert completed_tombstone.metadata_json["deleted_counts_json"] == {"raw_events": 1}
    assert "target_id_ref" not in completed_tombstone.metadata_json
    assert "lease_owner_id" not in completed_tombstone.metadata_json
    assert completed_job.status == LifecycleActionStatus.COMPLETED
    assert completed_job.destination_ref == "payload://exports/ws_1.jsonl"


@pytest.mark.asyncio
async def test_lifecycle_queue_retries_executor_failures_and_stale_leases() -> None:
    repository = InMemoryLifecycleRepository()
    service = LifecycleService(repository)
    tombstone = await service.request_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_1",
        requested_by_user_id="usr_1",
        reason="customer_request",
        queue_execution=True,
    )
    repository.lease_deletion_tombstone(
        tombstone_id=tombstone.id,
        worker_id="dead_worker",
        lease_expires_at=datetime(2026, 5, 14, tzinfo=UTC) - timedelta(minutes=1),
    )
    worker = LifecycleQueueWorker(
        service=service,
        deletion_executor=RecordingDeletionExecutor(fail=True),
        export_executor=RecordingExportExecutor(),
        worker_id="worker_1",
    )

    result = await worker.process_once(now=datetime(2026, 5, 14, tzinfo=UTC))

    assert result.retries_scheduled == 2
    assert result.failures == 1
    retried = repository.get_deletion_tombstone(tombstone.id)
    assert retried.status == LifecycleActionStatus.REQUESTED
    assert retried.metadata_json["last_error_code"] == "executor_failed"
    assert "lease_owner_id" not in retried.metadata_json


@pytest.mark.asyncio
async def test_lifecycle_repository_rejects_terminal_record_leases() -> None:
    repository = InMemoryLifecycleRepository()
    service = LifecycleService(repository)
    tombstone = await service.request_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_1",
        requested_by_user_id="usr_1",
        reason="customer_request",
        queue_execution=True,
    )
    repository.complete_deletion_tombstone(
        tombstone_id=tombstone.id,
        deleted_counts_json={"raw_events": 1},
    )

    with pytest.raises(LifecycleLeaseUnavailable):
        repository.lease_deletion_tombstone(
            tombstone_id=tombstone.id,
            worker_id="worker_1",
            lease_expires_at=datetime(2026, 5, 14, tzinfo=UTC),
        )
