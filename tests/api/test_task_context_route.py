from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.auth.dependencies import AUTH_EMAIL_HEADER
from cortex.config import Settings
from cortex.runtime import create_local_runtime
from cortex.ui.auth import WORKSPACE_ID_HEADER


def _client() -> tuple[TestClient, dict[str, str]]:
    app = create_app(
        Settings(cortex_public_auth_enabled=True),
        cortex_runtime=create_local_runtime(),
    )
    repository = app.state.tenant_repository
    user = repository.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    _, workspace, _ = repository.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    return TestClient(app), {
        AUTH_EMAIL_HEADER: "owner@example.com",
        WORKSPACE_ID_HEADER: workspace.id,
        "x-request-id": "task-context-trace",
    }


def test_task_context_http_route_uses_authenticated_authority() -> None:
    client, headers = _client()

    response = client.post(
        "/v1/context/task-context",
        headers=headers,
        json={
            "task": {
                "objective": "Investigate COR-123",
                "issue_ids": ["COR-123"],
                "pull_request_numbers": [42],
                "file_hints": ["src/cortex/runtime/context.py"],
            },
            "filters": {"providers": ["slack"], "source_ids": ["so_1"]},
            "budget": {"maximum_evidence_items": 1, "maximum_tokens": 10},
        },
    )

    assert response.status_code == 200
    assert response.json()["contract_version"] == "cortex.task_context.v1"
    assert response.json()["trace_id"] == "task-context-trace"
    assert response.json()["live_data"] is False


def test_task_context_http_route_rejects_client_tenancy_fields() -> None:
    client, headers = _client()

    response = client.post(
        "/v1/context/task-context",
        headers=headers,
        json={
            "workspace_id": "another-workspace",
            "task": {"objective": "Investigate COR-123"},
        },
    )

    assert response.status_code == 422
