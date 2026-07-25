import hashlib
import hmac
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def client() -> TestClient:
    return TestClient(
        create_app(
            Settings(
                cortex_slack_connector_enabled=True,
                slack_client_id="",
                slack_client_secret="",
                slack_signing_secret="test-secret",
                slack_redirect_uri="",
            )
        )
    )


def installed_client() -> TestClient:
    app = client()
    start = app.post("/connectors/slack/oauth/start", json={"workspace_id": "ws_1"})
    complete = app.post(
        "/connectors/slack/oauth/complete",
        json={"code": "oauth_code", "state": start.json()["state"]},
    )
    app.post(
        "/connectors/slack/sources/select",
        json={
            "workspace_id": "ws_1",
            "oauth_installation_id": complete.json()["installation"]["id"],
            "channels": [{"id": "C123", "name": "private-roadmap"}],
        },
    )
    return app


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
    app = installed_client()
    body = {"type": "url_verification", "challenge": "challenge-value"}
    headers = signed_headers(body, "test-secret")

    response = app.post(
        "/connectors/slack/events",
        params={"workspace_id": "ws_1"},
        content=json.dumps(body, separators=(",", ":")),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["challenge"] == "challenge-value"


def test_slack_webhook_persists_selected_message_without_content_leak() -> None:
    app = installed_client()
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
        params={"workspace_id": "ws_1"},
        content=json.dumps(body, separators=(",", ":")),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "persisted"
    assert response.json()["raw_event_created"] is True
    assert "private message text" not in response.text


def test_slack_webhook_rejects_invalid_signature() -> None:
    app = installed_client()

    response = app.post(
        "/connectors/slack/events",
        params={"workspace_id": "ws_1"},
        content='{"event_id":"Ev123"}',
        headers={
            "x-slack-request-timestamp": "1700000000",
            "x-slack-signature": "v0=bad",
        },
    )

    assert response.status_code == 401


def test_slack_health_route_is_content_free() -> None:
    app = installed_client()

    response = app.get("/connectors/slack/health/ws_1")

    assert response.status_code == 200
    assert response.json()["provider"] == "slack"
    assert response.json()["selected_channel_count"] == 1
    assert "private-roadmap" not in response.text
