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


def test_slack_oauth_get_start_redirects_when_configured() -> None:
    app = TestClient(
        create_app(
            Settings(
                cortex_slack_connector_enabled=True,
                slack_client_id="client-id",
                slack_client_secret="",
                slack_signing_secret="test-secret",
                slack_redirect_uri="http://localhost/callback",
            )
        )
    )

    response = app.get(
        "/connectors/slack/oauth/start",
        params={"workspace_id": "ws_1"},
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
