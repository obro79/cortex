import hashlib
import hmac
import json
from datetime import UTC, datetime

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
        workspace_slug="engineering",
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
    return TestClient(app), {
        AUTH_EMAIL_HEADER: "owner@example.com",
        WORKSPACE_ID_HEADER: workspace.id,
    }


def installed_client() -> tuple[TestClient, dict[str, str]]:
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
    app.post(
        "/connectors/slack/sources/select",
        json={
            "workspace_id": workspace_id,
            "oauth_installation_id": complete.json()["installation"]["id"],
            "channels": [{"id": "C123", "name": "private-roadmap"}],
        },
        headers=headers,
    )
    return app, headers


def signed_headers(body: dict[str, object], secret: str) -> dict[str, str]:
    timestamp = str(int(datetime.now(UTC).timestamp()))
    raw = json.dumps(body, separators=(",", ":")).encode()
    base = b"v0:" + timestamp.encode() + b":" + raw
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return {
        "x-slack-request-timestamp": timestamp,
        "x-slack-signature": signature,
        "content-type": "application/json",
    }


def test_slack_webhook_challenge_and_signature() -> None:
    app, auth_headers = installed_client()
    body = {"type": "url_verification", "challenge": "challenge-value"}
    headers = signed_headers(body, "test-secret")

    response = app.post(
        "/connectors/slack/events",
        params={"workspace_id": auth_headers[WORKSPACE_ID_HEADER]},
        content=json.dumps(body, separators=(",", ":")),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["challenge"] == "challenge-value"


def test_slack_webhook_persists_selected_message_without_content_leak() -> None:
    app, auth_headers = installed_client()
    body = {
        "event_id": "Ev123",
        "event_time": 1_700_000_000,
        "event": {
            "type": "message",
            "channel": "C123",
            "ts": "1700000000.000100",
            "text": "private message text",
        },
    }
    headers = signed_headers(body, "test-secret")

    response = app.post(
        "/connectors/slack/events",
        params={"workspace_id": auth_headers[WORKSPACE_ID_HEADER]},
        content=json.dumps(body, separators=(",", ":")),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "persisted"
    assert response.json()["raw_event_created"] is True
    assert response.json()["pipeline"] == {
        "processed_event_count": 5,
        "normalization_count": 1,
        "chunking_count": 1,
        "embedding_count": 2,
    }
    assert "private message text" not in response.text
    services = app.app.state.slack_connector
    assert [event.event_type for event in services.event_bus.list_events()] == [
        "raw_event.persisted",
        "source_object.upserted",
        "source_chunk.upserted",
        "embedding.requested",
        "embedding.completed",
    ]
    assert "private message text" not in str(
        [event.payload for event in services.event_bus.list_events()]
    )


def test_slack_webhook_rejects_invalid_signature() -> None:
    app, auth_headers = installed_client()

    response = app.post(
        "/connectors/slack/events",
        params={"workspace_id": auth_headers[WORKSPACE_ID_HEADER]},
        content='{"event_id":"Ev123"}',
        headers={
            "x-slack-request-timestamp": "1700000000",
            "x-slack-signature": "v0=bad",
        },
    )

    assert response.status_code == 401


def test_slack_webhook_ignores_unmapped_team_without_raw_event() -> None:
    app, auth_headers = installed_client()
    body = {
        "event_id": "Ev999",
        "context_team_id": "T_UNKNOWN",
        "event_time": 1_700_000_000,
        "event": {
            "type": "message",
            "channel": "C123",
            "ts": "1700000000.000999",
            "text": "should not persist",
        },
    }
    headers = signed_headers(body, "test-secret")

    response = app.post(
        "/connectors/slack/events",
        params={"workspace_id": auth_headers[WORKSPACE_ID_HEADER]},
        content=json.dumps(body, separators=(",", ":")),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored_unmapped_team"
    assert response.json()["raw_event_created"] is False
    services = app.app.state.slack_connector
    assert services.raw_events.list_all() == []


def test_slack_health_route_is_content_free() -> None:
    app, headers = installed_client()

    response = app.get(
        f"/connectors/slack/health/{headers[WORKSPACE_ID_HEADER]}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "slack"
    assert response.json()["selected_channel_count"] == 1
    assert "private-roadmap" not in response.text
