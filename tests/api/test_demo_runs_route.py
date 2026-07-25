from __future__ import annotations

from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.auth.dependencies import AUTH_EMAIL_HEADER
from cortex.config import Settings
from cortex.demo_runs import FixtureDemoRunReportReader, SqlAlchemyDemoRunReportStore
from cortex.ui.auth import WORKSPACE_ID_HEADER


def _client(
    *, reader: object | None = None, dev_workbench: bool = False
) -> tuple[TestClient, dict[str, str]]:
    app = create_app(
        Settings(
            cortex_public_auth_enabled=True,
            cortex_dev_workbench_enabled=dev_workbench,
        )
    )
    if reader is not None:
        app.state.demo_run_report_reader = reader
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
        "x-request-id": "demo-run-trace",
    }


def test_latest_demo_run_is_explicitly_unavailable_for_fixture_data() -> None:
    client, headers = _client(reader=FixtureDemoRunReportReader())

    response = client.get("/v1/demo-runs/latest", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["trace_id_hash"].startswith("sha256:")
    assert body["report"] is None
    assert "https://" not in response.text
    assert "Postgres is the approved" not in response.text
    assert "citation_url" not in response.text


def test_source_health_returns_fixture_projection_without_live_report() -> None:
    client, headers = _client(reader=FixtureDemoRunReportReader())

    response = client.get("/v1/demo-runs/source-health", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["readiness"] == "partial"
    assert body["freshness"] == "fresh"
    assert {source["mode"] for source in body["sources"]} == {"fixture"}


def test_local_workbench_registers_fixture_source_health() -> None:
    client, headers = _client(dev_workbench=True)

    response = client.get("/v1/demo-runs/source-health", headers=headers)

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert {source["mode"] for source in response.json()["sources"]} == {"fixture"}


def test_sql_state_registers_durable_report_store_without_connecting() -> None:
    app = create_app(
        Settings(
            cortex_state_backend="sql",
            database_url="postgresql+asyncpg://user:pass@localhost/cortex",
        )
    )

    assert isinstance(app.state.demo_run_report_store, SqlAlchemyDemoRunReportStore)
    assert app.state.demo_run_report_reader is app.state.demo_run_report_store


class _FailingDemoRunReader:
    async def latest_report(self, *, workspace_id: str, trace_id: str) -> None:
        del workspace_id, trace_id
        raise RuntimeError("database password must not be returned")


def test_latest_demo_run_fails_closed_when_reader_errors() -> None:
    client, headers = _client(reader=_FailingDemoRunReader())

    response = client.get("/v1/demo-runs/latest", headers=headers)

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert "database password" not in response.text
