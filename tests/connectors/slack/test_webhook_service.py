import json

from cortex.contracts.enums import WebhookDeliveryStatus

from .helpers import installed_selected_services, signed_headers


async def test_webhook_verifies_signature_and_persists_selected_message() -> None:
    services, _install, _selected = await installed_selected_services()
    body = {
        "event_id": "Ev123",
        "event_time": 1_700_000_000,
        "event": {
            "type": "message",
            "channel": "C123",
            "ts": "1700000000.000100",
            "text": "private message text",
        },
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    headers = signed_headers(body, "test-secret")

    result = await services.webhooks.handle(
        workspace_id="ws_1",
        body=raw,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )

    assert result.ok is True
    assert result.status == "persisted"
    assert result.raw_event_created is True
    event = services.event_bus.list_events()[0]
    assert event.event_type == "raw_event.persisted"
    assert event.provider == "slack"
    assert "private message text" not in str(event.payload)


async def test_webhook_resolves_workspace_from_slack_team_id() -> None:
    services, _install, _selected = await installed_selected_services()
    body = {
        "team_id": "T_TEST",
        "event_id": "EvTeam",
        "event_time": 1_700_000_000,
        "event": {
            "type": "message",
            "team": "T_TEST",
            "channel": "C123",
            "ts": "1700000000.000200",
        },
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    headers = signed_headers(body, "test-secret")

    result = await services.webhooks.handle(
        workspace_id="T_TEST",
        body=raw,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )

    assert result.status == "persisted"
    event = services.event_bus.list_events()[0]
    assert event.workspace_id == "ws_1"


async def test_webhook_duplicate_retry_noops() -> None:
    services, _install, _selected = await installed_selected_services()
    body = {
        "event_id": "Ev123",
        "event_time": 1_700_000_000,
        "event": {"type": "message", "channel": "C123", "ts": "1700000000.000100"},
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    headers = signed_headers(body, "test-secret")

    first = await services.webhooks.handle(
        workspace_id="ws_1",
        body=raw,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )
    second = await services.webhooks.handle(
        workspace_id="ws_1",
        body=raw,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
        retry_num="1",
    )

    assert first.raw_event_created is True
    assert second.status == WebhookDeliveryStatus.IGNORED_DUPLICATE
    assert second.raw_event_created is False


async def test_bad_signature_rejected_before_processing() -> None:
    services, _install, _selected = await installed_selected_services()

    result = await services.webhooks.handle(
        workspace_id="ws_1",
        body=b'{"event_id":"Ev123"}',
        timestamp="1700000000",
        signature="v0=bad",
    )

    assert result.ok is False
    assert result.error == "bad_signature"
    assert services.event_bus.list_events() == []


async def test_unselected_channel_is_ignored_without_raw_event() -> None:
    services, _install, _selected = await installed_selected_services()
    body = {
        "event_id": "Ev999",
        "event_time": 1_700_000_000,
        "event": {"type": "message", "channel": "C999", "ts": "1700000000.000100"},
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    headers = signed_headers(body, "test-secret")

    result = await services.webhooks.handle(
        workspace_id="ws_1",
        body=raw,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )

    assert result.ok is True
    assert result.status == "ignored_unselected"
    assert services.event_bus.list_events() == []
