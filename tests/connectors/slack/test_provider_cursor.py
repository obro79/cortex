from cortex.connectors.slack.client import SlackPermanentError, SlackRateLimitError
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.contracts.enums import BackfillJobStatus


class RateLimitedClient:
    async def conversation_history(self, **kwargs):
        raise SlackRateLimitError("retry later")

    async def thread_replies(self, **kwargs):
        return []


class BrokenClient:
    async def conversation_history(self, **kwargs):
        raise SlackPermanentError("bad auth")

    async def thread_replies(self, **kwargs):
        return []


async def selected_source_id(services) -> str:
    start = services.oauth.start_install(workspace_id="ws_1")
    complete = await services.oauth.complete_install(
        code="code_123", state=str(start["state"])
    )
    selected = services.sources.select_channels(
        workspace_id="ws_1",
        oauth_installation_id=complete["installation"]["id"],
        channels=[{"id": "C123"}],
    )
    return str(selected["source_connections"][0]["id"])


async def test_rate_limit_marks_backfill_retrying_without_cursor_advance() -> None:
    services = create_slack_connector_services(slack_client=RateLimitedClient())
    source_id = await selected_source_id(services)

    result = await services.backfill.backfill_source(
        workspace_id="ws_1", source_connection_id=source_id
    )

    assert result.ok is False
    assert result.job.status == BackfillJobStatus.RETRYING
    assert result.cursor_value is None
    assert (
        services.cursors.get_for_source(
            workspace_id="ws_1", source_connection_id=source_id
        )
        is None
    )


async def test_permanent_failure_deadletters_backfill_job() -> None:
    services = create_slack_connector_services(slack_client=BrokenClient())
    source_id = await selected_source_id(services)

    result = await services.backfill.backfill_source(
        workspace_id="ws_1", source_connection_id=source_id
    )

    assert result.ok is False
    assert result.job.status == BackfillJobStatus.DEADLETTERED
    assert result.job.last_error_code == "permanent_failure"
