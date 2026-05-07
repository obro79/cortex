from cortex.connectors.slack.client import SlackHistoryPage
from cortex.connectors.slack.service import create_slack_connector_services


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
    selected = services.sources.select_channels(
        workspace_id="ws_1",
        oauth_installation_id=complete["installation"]["id"],
        channels=[{"id": "C123"}],
    )
    source_id = selected["source_connections"][0]["id"]

    await services.backfill.backfill_source(
        workspace_id="ws_1", source_connection_id=source_id
    )
    health = services.health.workspace_health("ws_1")

    assert health["provider"] == "slack"
    assert health["selected_channel_count"] == 1
    assert health["cursor_count"] == 1
    assert health["newest_cursor"] == "1700000000.1"
    assert health["deadletter_count"] == 0
    assert "C123" not in str(health)
