from __future__ import annotations

from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.auth.dependencies import AUTH_EMAIL_HEADER
from cortex.config import Settings
from cortex.lifecycle import LifecycleExportResult
from cortex.tenancy import InMemoryTenantRepository
from cortex.ui.auth import WORKSPACE_ID_HEADER


class RecordingDeletionExecutor:
    def __init__(self) -> None:
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
        return {"raw_events": 1}


class RecordingExportExecutor:
    def export(
        self,
        *,
        workspace_id: str,
        export_scope: str,
    ) -> LifecycleExportResult:
        return LifecycleExportResult(
            destination_ref=f"payload://exports/{workspace_id}.jsonl",
            metadata_json={"counts": {"raw_events": 1}},
        )


def test_lifecycle_deletion_route_request_status_lease_execute_retry() -> None:
    app = create_app(Settings(cortex_public_auth_enabled=True))
    deletion_executor = RecordingDeletionExecutor()
    app.state.lifecycle_deletion_executor = deletion_executor
    headers = _seed_owner(app)
    client = TestClient(app)

    created = client.post(
        "/lifecycle/deletions",
        json={
            "workspace_id": headers[WORKSPACE_ID_HEADER],
            "target_type": "source_connection",
            "target_id": "src_1",
            "reason": "customer_request",
        },
        headers=headers,
    )
    tombstone_id = created.json()["id"]
    status = client.get(
        f"/lifecycle/deletions/{headers[WORKSPACE_ID_HEADER]}/{tombstone_id}",
        headers=headers,
    )
    leased = client.post(
        f"/lifecycle/deletions/{headers[WORKSPACE_ID_HEADER]}/{tombstone_id}/lease",
        json={"worker_id": "worker_1"},
        headers=headers,
    )
    executed = client.post(
        f"/lifecycle/deletions/{headers[WORKSPACE_ID_HEADER]}/{tombstone_id}/execute",
        headers=headers,
    )
    retried = client.post(
        f"/lifecycle/deletions/{headers[WORKSPACE_ID_HEADER]}/{tombstone_id}/retry",
        headers=headers,
    )

    assert created.status_code == 200
    assert "target_id_ref" not in created.json()["metadata_json"]
    assert status.status_code == 200
    assert leased.status_code == 200
    assert leased.json()["metadata_json"]["lease_owner_id"] == "worker_1"
    assert executed.status_code == 200
    assert executed.json()["status"] == "completed"
    assert deletion_executor.calls == [
        {
            "workspace_id": headers[WORKSPACE_ID_HEADER],
            "target_type": "source_connection",
            "target_id": "src_1",
        }
    ]
    assert retried.status_code == 200
    assert retried.json()["status"] == "requested"


def test_lifecycle_export_route_request_status_lease_execute_retry() -> None:
    app = create_app(Settings(cortex_public_auth_enabled=True))
    app.state.lifecycle_export_executor = RecordingExportExecutor()
    headers = _seed_owner(app)
    client = TestClient(app)

    created = client.post(
        "/lifecycle/exports",
        json={
            "workspace_id": headers[WORKSPACE_ID_HEADER],
            "export_scope": "workspace",
        },
        headers=headers,
    )
    job_id = created.json()["id"]
    status = client.get(
        f"/lifecycle/exports/{headers[WORKSPACE_ID_HEADER]}/{job_id}",
        headers=headers,
    )
    leased = client.post(
        f"/lifecycle/exports/{headers[WORKSPACE_ID_HEADER]}/{job_id}/lease",
        json={"worker_id": "worker_1"},
        headers=headers,
    )
    executed = client.post(
        f"/lifecycle/exports/{headers[WORKSPACE_ID_HEADER]}/{job_id}/execute",
        headers=headers,
    )
    retried = client.post(
        f"/lifecycle/exports/{headers[WORKSPACE_ID_HEADER]}/{job_id}/retry",
        headers=headers,
    )

    assert created.status_code == 200
    assert status.status_code == 200
    assert leased.status_code == 200
    assert executed.status_code == 200
    assert executed.json()["status"] == "completed"
    assert executed.json()["destination_ref"] == (
        f"payload://exports/{headers[WORKSPACE_ID_HEADER]}.jsonl"
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "requested"


def _seed_owner(app: object) -> dict[str, str]:
    repo: InMemoryTenantRepository = app.state.tenant_repository
    user = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    _, workspace, _ = repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    return {
        AUTH_EMAIL_HEADER: "owner@example.com",
        WORKSPACE_ID_HEADER: workspace.id,
    }
