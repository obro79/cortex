from cortex.contracts.enums import SourceConnectionStatus

from .helpers import installed_selected_services


async def test_selected_channels_create_source_connections_without_names() -> None:
    services, _install, selected = await installed_selected_services()

    source = selected["source_connections"][0]
    assert source["external_source_id"] == "C123"
    assert source["status"] == SourceConnectionStatus.ACTIVE
    assert source["display_name_hash"].startswith("sha256:")
    assert "private-roadmap" not in str(source)
    assert services.source_connections.get_selected_channel("ws_1", "C123") is not None


async def test_unselected_channel_lookup_returns_none() -> None:
    services, _install, _selected = await installed_selected_services()

    assert services.source_connections.get_selected_channel("ws_1", "C999") is None
