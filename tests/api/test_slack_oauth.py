from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def client() -> TestClient:
    return TestClient(
        create_app(
            Settings(
                cortex_slack_connector_enabled=True,
                slack_signing_secret="test-secret",
            )
        )
    )


def test_slack_oauth_routes_redact_token_material() -> None:
    app = client()

    start = app.post(
        "/connectors/slack/oauth/start",
        json={"workspace_id": "ws_1", "actor_id": "human_1"},
    )
    complete = app.post(
        "/connectors/slack/oauth/complete",
        json={"code": "oauth_code", "state": start.json()["state"]},
    )

    assert start.status_code == 200
    assert complete.status_code == 200
    assert complete.json()["installation"]["status"] == "active"
    assert "token-material" not in complete.text


def test_slack_source_selection_route() -> None:
    app = client()
    start = app.post("/connectors/slack/oauth/start", json={"workspace_id": "ws_1"})
    complete = app.post(
        "/connectors/slack/oauth/complete",
        json={"code": "oauth_code", "state": start.json()["state"]},
    )

    selected = app.post(
        "/connectors/slack/sources/select",
        json={
            "workspace_id": "ws_1",
            "oauth_installation_id": complete.json()["installation"]["id"],
            "channels": [{"id": "C123", "name": "private-roadmap"}],
        },
    )

    assert selected.status_code == 200
    assert selected.json()["source_connections"][0]["external_source_id"] == "C123"
    assert "private-roadmap" not in selected.text
