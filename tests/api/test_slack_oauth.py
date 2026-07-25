from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.auth.dependencies import AUTH_EMAIL_HEADER
from cortex.billing import BillingStatus, SubscriptionStatus
from cortex.config import Settings
from cortex.ui.auth import WORKSPACE_ID_HEADER


def client() -> tuple[TestClient, dict[str, str]]:
    app = create_app(
        Settings(
            cortex_slack_connector_enabled=True,
            cortex_public_auth_enabled=True,
            slack_client_id="",
            slack_client_secret="",
            slack_signing_secret="test-secret",
            slack_redirect_uri="",
        )
    )
    return TestClient(app), seed_owner_context(app, "ws_1")


def seed_owner_context(app: FastAPI, workspace_slug: str) -> dict[str, str]:
    repo = app.state.tenant_repository
    user = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    organization, workspace, _ = repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug=workspace_slug,
    )
    customer = app.state.billing_repository.ensure_customer(
        organization_id=organization.id,
        status=BillingStatus.TRIALING,
    )
    app.state.billing_repository.upsert_subscription(
        organization_id=organization.id,
        billing_customer_id=customer.id,
        plan_id="free_trial",
        status=SubscriptionStatus.TRIALING,
    )
    return {
        AUTH_EMAIL_HEADER: "owner@example.com",
        WORKSPACE_ID_HEADER: workspace.id,
    }


def test_slack_oauth_routes_redact_token_material() -> None:
    app, headers = client()
    workspace_id = headers[WORKSPACE_ID_HEADER]

    start = app.post(
        "/connectors/slack/oauth/start",
        json={"workspace_id": workspace_id, "actor_id": "human_1"},
        headers=headers,
    )
    complete = app.post(
        "/connectors/slack/oauth/complete",
        json={"code": "oauth_code", "state": start.json()["state"]},
    )

    assert start.status_code == 200
    assert complete.status_code == 200
    assert complete.json()["installation"]["status"] == "active"
    assert "token-material" not in complete.text


def test_slack_oauth_get_start_redirects_when_configured() -> None:
    raw_app = create_app(
        Settings(
            cortex_slack_connector_enabled=True,
            cortex_public_auth_enabled=True,
            slack_client_id="client-id",
            slack_client_secret="",
            slack_signing_secret="test-secret",
            slack_redirect_uri="http://localhost/callback",
        )
    )
    headers = seed_owner_context(raw_app, "ws_1")
    app = TestClient(raw_app)

    response = app.get(
        "/connectors/slack/oauth/start",
        params={"workspace_id": headers[WORKSPACE_ID_HEADER]},
        headers=headers,
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"].startswith(
        "https://slack.com/oauth/v2/authorize?"
    )


def test_sql_slack_connector_requires_secret_encryption_key(tmp_path) -> None:
    try:
        create_app(
            Settings(
                _env_file=None,
                cortex_slack_connector_enabled=True,
                cortex_state_backend="sql",
                cortex_event_bus="kafka",
                database_url="postgresql+asyncpg://localhost/cortex",
                kafka_bootstrap_servers="localhost:9092",
                payload_store_path=str(tmp_path / "payloads"),
            )
        )
    except ValueError as error:
        assert "CORTEX_SECRET_ENCRYPTION_KEY" in str(error)
    else:
        raise AssertionError("SQL Slack connector should require encryption key")


def test_slack_source_selection_route() -> None:
    app, headers = client()
    workspace_id = headers[WORKSPACE_ID_HEADER]
    start = app.post(
        "/connectors/slack/oauth/start",
        json={"workspace_id": workspace_id},
        headers=headers,
    )
    complete = app.post(
        "/connectors/slack/oauth/complete",
        json={"code": "oauth_code", "state": start.json()["state"]},
    )

    selected = app.post(
        "/connectors/slack/sources/select",
        json={
            "workspace_id": workspace_id,
            "oauth_installation_id": complete.json()["installation"]["id"],
            "channels": [{"id": "C123", "name": "private-roadmap"}],
        },
        headers=headers,
    )

    assert selected.status_code == 200
    assert selected.json()["source_connections"][0]["external_source_id"] == "C123"
    assert "private-roadmap" not in selected.text


def test_slack_source_selection_requires_workspace_membership() -> None:
    app, headers = client()
    denied = app.post(
        "/connectors/slack/sources/select",
        json={
            "workspace_id": "ws_other",
            "oauth_installation_id": "oauth_1",
            "channels": [{"id": "C123", "name": "private-roadmap"}],
        },
        headers=headers,
    )

    assert denied.status_code == 403


def test_slack_source_selection_enforces_plan_limit() -> None:
    app = create_app(
        Settings(
            cortex_slack_connector_enabled=True,
            cortex_public_auth_enabled=True,
            slack_signing_secret="test-secret",
        )
    )
    repo = app.state.tenant_repository
    user = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Invite Only",
        workspace_name="Invite Only",
        workspace_slug="ws_invite",
    )
    workspace_id = next(iter(repo.workspaces))
    headers = {
        AUTH_EMAIL_HEADER: "owner@example.com",
        WORKSPACE_ID_HEADER: workspace_id,
    }
    client_app = TestClient(app)
    start = client_app.post(
        "/connectors/slack/oauth/start",
        json={"workspace_id": workspace_id},
        headers=headers,
    )
    complete = client_app.post(
        "/connectors/slack/oauth/complete",
        json={"code": "oauth_code", "state": start.json()["state"]},
    )

    response = client_app.post(
        "/connectors/slack/sources/select",
        json={
            "workspace_id": workspace_id,
            "oauth_installation_id": complete.json()["installation"]["id"],
            "channels": [{"id": "C123", "name": "private-roadmap"}],
        },
        headers=headers,
    )

    assert response.status_code == 402
    assert response.json()["detail"]["reason"] == "plan_limit_exceeded"
