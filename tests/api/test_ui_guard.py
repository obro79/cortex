from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.ui.auth import (
    ACTOR_ID_HEADER,
    CSRF_HEADER,
    ROLES_HEADER,
    SESSION_ID_HEADER,
    WORKSPACE_ID_HEADER,
    issue_csrf_token,
)
from cortex.ui.source_health import SourceHealthViewService
from cortex.utils.asyncio import maybe_await


def test_ui_routes_unavailable_when_disabled() -> None:
    client = TestClient(create_app(Settings(cortex_ui_enabled=False)))

    response = client.get("/ui")

    assert response.status_code == 404


def test_ui_requires_explicit_internal_admin_session_flag() -> None:
    client = TestClient(create_app(Settings(cortex_ui_enabled=True)))

    response = client.get("/ui", headers=_session_headers())

    assert response.status_code == 401


def test_ui_requires_internal_actor_headers() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_ui_enabled=True,
                cortex_internal_admin_session_enabled=True,
            )
        )
    )

    response = client.get("/ui")

    assert response.status_code == 401


def test_ui_overview_renders_for_internal_admin_actor() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_ui_enabled=True,
                cortex_internal_admin_session_enabled=True,
            )
        )
    )

    response = client.get("/ui", headers=_session_headers())

    assert response.status_code == 200
    assert "Operations Overview" in response.text
    assert "Workspace ws_1" in response.text
    assert "xoxb" not in response.text


def test_internal_session_start_sets_cookies_for_browser_preview() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_ui_enabled=True,
                cortex_internal_admin_session_enabled=True,
            )
        ),
        follow_redirects=False,
    )

    response = client.get(
        "/ui/internal/session/start?workspace_id=ws_1&actor_id=actor_1"
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/ui"
    assert "cortex_ui_workspace_id=ws_1" in response.headers["set-cookie"]


def test_internal_session_start_is_not_available_in_production() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_env="production",
                cortex_ui_enabled=True,
                cortex_internal_admin_session_enabled=True,
            )
        )
    )

    response = client.get("/ui/internal/session/start")

    assert response.status_code == 404


def test_ui_overview_accepts_internal_session_cookies() -> None:
    client = TestClient(
        create_app(
            Settings(
                cortex_ui_enabled=True,
                cortex_internal_admin_session_enabled=True,
            )
        )
    )

    start_response = client.get("/ui/internal/session/start")
    assert start_response.status_code == 200
    response = client.get("/ui")

    assert response.status_code == 200
    assert "Workspace ws_live_slack" in response.text


async def test_ui_sources_render_real_slack_state_without_private_values() -> None:
    services = create_slack_connector_services()
    start = services.oauth.start_install(workspace_id="ws_1", actor_id="human_1")
    complete = await services.oauth.complete_install(
        code="code_123",
        state=str(start["state"]),
    )
    selected = await services.sources.select_channels(
        workspace_id="ws_1",
        oauth_installation_id=str(complete["installation"]["id"]),
        channels=[
            {
                "id": "C123",
                "name": "private-roadmap",
                "private_url": "https://files.slack.com/private",
            }
        ],
    )
    source_id = str(selected["source_connections"][0]["id"])
    await maybe_await(
        services.cursors.advance_after_persist(
            workspace_id="ws_1",
            source_connection_id=source_id,
            event_ts="1700000000.1",
        )
    )
    job = await maybe_await(
        services.backfills.create(
            workspace_id="ws_1",
            source_connection_id=source_id,
        )
    )
    await maybe_await(services.backfills.mark_completed(job.id, cursor_id=None))
    app = create_app(
        Settings(
            cortex_ui_enabled=True,
            cortex_internal_admin_session_enabled=True,
        )
    )
    app.state.source_health_view = SourceHealthViewService(slack_connector=services)
    client = TestClient(app)

    response = client.get("/ui/sources", headers=_session_headers())

    assert response.status_code == 200
    assert "Source Health" in response.text
    assert "1700000000.1" in response.text
    assert "completed" in response.text
    assert "C123" not in response.text
    assert "private-roadmap" not in response.text
    assert "files.slack.com" not in response.text
    assert "slack-token-material" not in response.text


async def test_ui_connectors_render_real_slack_summary() -> None:
    services = create_slack_connector_services()
    start = services.oauth.start_install(workspace_id="ws_1", actor_id="human_1")
    complete = await services.oauth.complete_install(
        code="code_123",
        state=str(start["state"]),
    )
    await services.sources.select_channels(
        workspace_id="ws_1",
        oauth_installation_id=str(complete["installation"]["id"]),
        channels=[{"id": "C123", "name": "private-roadmap"}],
    )
    app = create_app(
        Settings(
            cortex_ui_enabled=True,
            cortex_internal_admin_session_enabled=True,
        )
    )
    app.state.source_health_view = SourceHealthViewService(slack_connector=services)
    client = TestClient(app)

    response = client.get("/ui/connectors", headers=_session_headers())

    assert response.status_code == 200
    assert "Connectors" in response.text
    assert "slack" in response.text
    assert "active" in response.text
    assert "T_TEST" in response.text
    assert "C123" not in response.text
    assert "private-roadmap" not in response.text


def test_ui_csrf_token_is_bound_to_session() -> None:
    settings = Settings(
        cortex_ui_enabled=True,
        cortex_internal_admin_session_enabled=True,
    )

    token = issue_csrf_token(
        settings=settings,
        workspace_id="ws_1",
        actor_id="actor_1",
        session_id="session_1",
    )

    assert len(token) == 64
    assert token != "session_1"
    assert token != issue_csrf_token(
        settings=settings,
        workspace_id="ws_1",
        actor_id="actor_1",
        session_id="session_2",
    )


def _session_headers() -> dict[str, str]:
    return {
        WORKSPACE_ID_HEADER: "ws_1",
        ACTOR_ID_HEADER: "actor_1",
        ROLES_HEADER: "workspace_admin",
        SESSION_ID_HEADER: "session_1",
        CSRF_HEADER: "unused-for-get",
    }
