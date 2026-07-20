from cortex.connectors.slack.client import SlackHistoryPage
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.contracts.enums import SourceConnectionStatus
from cortex.permissions.scopes import scope_external_id_hash

from .helpers import installed_selected_services


class ChannelListClient:
    async def conversations_list(
        self,
        *,
        access_token: str,
        cursor: str | None = None,
        types: str = "public_channel,private_channel",
    ) -> SlackHistoryPage:
        return SlackHistoryPage(
            messages=[
                {
                    "id": "C123",
                    "name": "private-roadmap",
                    "is_private": True,
                    "is_member": True,
                }
            ],
            next_cursor="next-page",
        )

    async def conversation_history(self, **kwargs):
        return SlackHistoryPage(messages=[])

    async def thread_replies(self, **kwargs):
        return []


async def test_selected_channels_create_source_connections_without_names() -> None:
    services, _install, selected = await installed_selected_services()

    source = selected["source_connections"][0]
    assert source["external_source_id"] == "C123"
    assert source["status"] == SourceConnectionStatus.ACTIVE
    assert source["display_name_hash"].startswith("sha256:")
    assert "private-roadmap" not in str(source)
    assert services.source_connections.get_selected_channel("ws_1", "C123") is not None
    scopes = services.permission_scope_repository.list_active("ws_1")
    assert len(scopes) == 1
    assert scopes[0].external_id_hash == scope_external_id_hash(
        "slack", "slack_channel", "C123"
    )


async def test_selection_rejects_workspace_mismatch() -> None:
    services = create_slack_connector_services()
    start = services.oauth.start_install(workspace_id="ws_internal")
    complete = await services.oauth.complete_install(
        code="code_123", state=str(start["state"])
    )

    try:
        await services.sources.select_channels(
            workspace_id="T_TEST",
            oauth_installation_id=complete["installation"]["id"],
            channels=[{"id": "C123", "name": "private-roadmap"}],
        )
    except PermissionError as error:
        assert str(error) == "workspace_mismatch"
    else:
        raise AssertionError("workspace mismatch should be rejected")
    assert (
        services.source_connections.get_selected_channel("ws_internal", "C123") is None
    )
    assert services.source_connections.get_selected_channel("T_TEST", "C123") is None
    assert services.permission_scope_repository.list_active("ws_internal") == []
    assert services.permission_scope_repository.list_active("T_TEST") == []


async def test_unselected_channel_lookup_returns_none() -> None:
    services, _install, _selected = await installed_selected_services()

    assert services.source_connections.get_selected_channel("ws_1", "C999") is None


async def test_list_channels_uses_installation_token_and_redacts_selection() -> None:
    services = create_slack_connector_services(slack_client=ChannelListClient())
    start = services.oauth.start_install(workspace_id="ws_1")
    complete = await services.oauth.complete_install(
        code="code_123", state=str(start["state"])
    )

    listed = await services.sources.list_channels(
        workspace_id="ws_1", oauth_installation_id=complete["installation"]["id"]
    )

    assert listed["ok"] is True
    assert listed["next_cursor"] == "next-page"
    assert listed["channels"] == [
        {
            "id": "C123",
            "name": "private-roadmap",
            "is_private": True,
            "is_member": True,
        }
    ]


async def test_deselect_channel_disables_source_and_prevents_selected_lookup() -> None:
    services, _install, selected = await installed_selected_services()
    source_id = selected["source_connections"][0]["id"]
    removed: list[tuple[str, str]] = []

    async def remove_indexed_data(workspace_id: str, source_connection_id: str) -> None:
        removed.append((workspace_id, source_connection_id))

    services.sources.removal_callback = remove_indexed_data

    result = await services.sources.deselect_channel(
        workspace_id="ws_1", source_connection_id=source_id
    )

    assert result["status"] == "disabled"
    assert result["source_connection"]["selected"] is False
    assert result["source_connection"]["status"] == SourceConnectionStatus.DISABLED
    assert services.source_connections.get_selected_channel("ws_1", "C123") is None
    assert services.permission_scope_repository.list_active("ws_1") == []
    assert removed == [("ws_1", source_id)]


async def test_deselect_fails_closed_without_cleanup_callback() -> None:
    services, _install, selected = await installed_selected_services()
    source_id = selected["source_connections"][0]["id"]

    result = await services.sources.deselect_channel(
        workspace_id="ws_1", source_connection_id=source_id
    )

    assert result["ok"] is False
    assert result["status"] == "removal_cleanup_unavailable"
    assert services.source_connections.get_selected_channel("ws_1", "C123") is not None
    assert len(services.permission_scope_repository.list_active("ws_1")) == 1
