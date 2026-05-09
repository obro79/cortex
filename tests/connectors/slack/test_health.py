from cortex.connectors.slack.client import SlackHistoryPage
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.contracts.enums import OAuthInstallationStatus


class OneMessageClient:
    async def conversation_history(self, **kwargs):
        return SlackHistoryPage(
            messages=[{"type": "message", "channel": "C123", "ts": "1700000000.1"}]
        )

    async def thread_replies(self, **kwargs):
        return []


async def test_health_reports_selected_channels_cursors_and_failures() -> None:
    services = create_slack_connector_services(slack_client=OneMessageClient())
    start = services.oauth.start_install(workspace_id="ws_1")
    complete = await services.oauth.complete_install(
        code="code_123", state=str(start["state"])
    )
    selected = await services.sources.select_channels(
        workspace_id="ws_1",
        oauth_installation_id=complete["installation"]["id"],
        channels=[{"id": "C123"}],
    )
    source_id = selected["source_connections"][0]["id"]

    await services.backfill.backfill_source(
        workspace_id="ws_1", source_connection_id=source_id
    )
    health = await services.health.workspace_health("ws_1")

    assert health["provider"] == "slack"
    assert health["selected_channel_count"] == 1
    assert health["cursor_count"] == 1
    assert health["newest_cursor"] == "1700000000.1"
    assert health["deadletter_count"] == 0
    assert health["oauth_status"] == OAuthInstallationStatus.ACTIVE
    assert "C123" not in str(health)


async def test_health_reports_missing_scope_reauth_status() -> None:
    services = create_slack_connector_services()
    start = services.oauth.start_install(workspace_id="ws_1")

    complete = await services.oauth.complete_install(
        code="code_123", state=str(start["state"])
    )
    install = services.installations.get_by_id(str(complete["installation"]["id"]))
    services.installations.upsert_active(
        workspace_id="ws_1",
        provider_workspace_id=install.provider_workspace_id,
        secret_ref_id=install.secret_ref_id,
        scopes={"channels:read"},
        status=OAuthInstallationStatus.NEEDS_REAUTH,
        health_json={"missing_scopes": ["channels:history"], "ok": False},
    )

    health = await services.health.workspace_health("ws_1")

    assert health["oauth_status"] == OAuthInstallationStatus.NEEDS_REAUTH
