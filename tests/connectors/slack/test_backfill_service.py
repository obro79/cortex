from __future__ import annotations

from typing import Any

from cortex.connectors.slack.client import SlackHistoryPage
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.contracts.enums import BackfillJobStatus


class FakeSlackClient:
    def __init__(self) -> None:
        self.history_calls = 0
        self.reply_calls = 0

    async def conversation_history(
        self,
        *,
        access_token: str,
        channel_id: str,
        cursor: str | None = None,
        oldest: str | None = None,
    ) -> SlackHistoryPage:
        self.history_calls += 1
        return SlackHistoryPage(
            messages=[
                {
                    "type": "message",
                    "channel": channel_id,
                    "ts": "1700000000.000100",
                    "text": "private session text",
                    "reply_count": 1,
                    "files": [
                        {
                            "id": "F123",
                            "name": "secret-roadmap.png",
                            "mimetype": "image/png",
                            "url_private": "https://files.slack.com/private",
                            "url_private_hash": "sha256:file-url",
                        }
                    ],
                    "links": [{"domain": "example.com", "url_hash": "sha256:url"}],
                }
            ],
            next_cursor=None,
        )

    async def thread_replies(
        self, *, access_token: str, channel_id: str, thread_ts: str
    ) -> list[dict[str, Any]]:
        self.reply_calls += 1
        return [
            {
                "type": "message",
                "channel": channel_id,
                "ts": "1700000001.000100",
                "thread_ts": thread_ts,
                "text": "private reply text",
            }
        ]


async def test_backfill_persists_messages_threads_files_links_and_cursor() -> None:
    fake = FakeSlackClient()
    services = create_slack_connector_services(slack_client=fake)
    start = services.oauth.start_install(workspace_id="ws_1")
    complete = await services.oauth.complete_install(
        code="code_123", state=str(start["state"])
    )
    selected = services.sources.select_channels(
        workspace_id="ws_1",
        oauth_installation_id=complete["installation"]["id"],
        channels=[{"id": "C123", "name": "private-roadmap"}],
    )
    source_id = selected["source_connections"][0]["id"]

    result = await services.backfill.backfill_source(
        workspace_id="ws_1", source_connection_id=source_id
    )

    assert result.ok is True
    assert result.job.status == BackfillJobStatus.COMPLETED
    assert result.raw_events_created == 4
    assert result.cursor_value == "1700000001.000100"
    assert fake.reply_calls == 1
    assert len(services.event_bus.list_events()) == 4
    event_payloads = [event.payload for event in services.event_bus.list_events()]
    assert {"provider_event_type": "file_shared"} in event_payloads
    assert "private session text" not in str(event_payloads)
    assert "secret-roadmap.png" not in str(event_payloads)


async def test_backfill_resume_counts_duplicates_without_rewriting_payloads() -> None:
    fake = FakeSlackClient()
    services = create_slack_connector_services(slack_client=fake)
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

    first = await services.backfill.backfill_source(
        workspace_id="ws_1", source_connection_id=source_id
    )
    second = await services.backfill.backfill_source(
        workspace_id="ws_1", source_connection_id=source_id
    )

    assert first.raw_events_created == 4
    assert second.raw_events_created == 0
    assert second.duplicates == 4
