from cortex.connectors.slack.mapping import derived_raw_events_for_message

from .helpers import installed_selected_services


async def test_file_and_link_metadata_are_safe_raw_event_inputs() -> None:
    services, _install, _selected = await installed_selected_services()
    source = services.source_connections.get_selected_channel("ws_1", "C123")
    assert source is not None

    events = derived_raw_events_for_message(
        workspace_id="ws_1",
        source=source,
        message={
            "ts": "1700000000.000100",
            "text": "private message",
            "files": [
                {
                    "id": "F123",
                    "name": "confidential.png",
                    "url_private": "https://files.slack.com/private",
                    "url_private_hash": "sha256:file-url",
                    "mimetype": "image/png",
                }
            ],
            "links": [{"domain": "example.com", "url_hash": "sha256:url"}],
        },
    )

    payload_text = str([event.payload for event in events])
    assert [event.event_type for event in events] == [
        "message",
        "file_shared",
        "link_shared",
    ]
    assert "confidential.png" not in payload_text
    assert "files.slack.com/private" not in payload_text
    assert "sha256:file-url" in payload_text
