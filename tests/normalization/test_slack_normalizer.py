from __future__ import annotations

import json
from datetime import UTC, datetime

from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus
from cortex.normalization.normalizers.slack import normalize_slack_payload


def raw_event(
    *,
    event_type: str = "message",
    external_object_key: str = "slack:T123:C123:1700000000.000100",
) -> RawEvent:
    now = datetime.now(UTC)
    return RawEvent(
        id="raw_slack_1",
        workspace_id="ws_1",
        source_connection_id="src_slack_1",
        provider="slack",
        external_event_id="Ev123",
        event_type=event_type,
        external_object_key=external_object_key,
        idempotency_key="slack:ws_1:C123:1700000000.000100:message",
        payload_ref="payload_1",
        payload_hash="sha256:payload",
        payload_size_bytes=128,
        occurred_at=None,
        received_at=now,
        status=RawEventStatus.PUBLISHED,
        created_at=now,
        updated_at=now,
    )


def event_payload(text: str = "Project comet launch decision") -> bytes:
    return json.dumps(
        {
            "team_id": "T123",
            "event_id": "Ev123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "ts": "1700000000.000100",
                "thread_ts": "1700000000.000100",
                "text": text,
                "reply_count": 2,
                "files": [
                    {
                        "id": "F123",
                        "name": "secret-roadmap.png",
                        "url_private": "https://files.slack.com/private",
                    }
                ],
                "links": [
                    {"url": "https://private.example/doc", "domain": "example.com"}
                ],
            },
        },
        separators=(",", ":"),
    ).encode()


def test_live_slack_message_payload_normalizes_to_stable_source_object() -> None:
    first = normalize_slack_payload(raw_event(), event_payload())
    second = normalize_slack_payload(raw_event(), event_payload())

    source = first.source_objects[0]

    assert source.id == second.source_objects[0].id
    assert source.object_type == "slack_thread"
    assert source.external_object_id == "T123:C123:1700000000.000100:1700000000.000100"
    assert source.title == "Slack thread"
    assert source.author_external_id == "U123"
    assert source.metadata_json["channel_id"] == "C123"
    assert source.metadata_json["channel_id_hash"] != "C123"
    assert source.metadata_json["reply_count"] == 2
    assert source.metadata_json["has_files"] is True
    assert source.metadata_json["has_links"] is True
    assert "retrieval_text" not in source.metadata_json
    assert "Project comet" not in str(source.metadata_json)
    assert source.content_text == "Project comet launch decision"


def test_backfill_slack_message_payload_normalizes() -> None:
    payload = {
        "event": {
            "type": "message",
            "channel": "C123",
            "user": "U123",
            "ts": "1700000000.000100",
            "text": "Backfilled channel launch note",
        },
        "source": {"channel_id": "C123", "source_connection_id": "src_slack_1"},
    }

    result = normalize_slack_payload(
        raw_event(external_object_key="slack:team:C123:1700000000.000100"),
        json.dumps(payload).encode(),
    )

    assert len(result.source_objects) == 1
    assert result.source_objects[0].external_object_id.startswith("team:C123:")
    assert result.source_objects[0].content_text == "Backfilled channel launch note"


def test_file_and_link_events_do_not_emit_private_metadata() -> None:
    payload = {
        "event": {
            "type": "file_shared",
            "channel": "C123",
            "message_ts": "1700000000.000100",
            "file": {
                "id": "F123",
                "name": "secret-roadmap.png",
                "url_private": "https://files.slack.com/private",
            },
        }
    }

    result = normalize_slack_payload(
        raw_event(event_type="file_shared"),
        json.dumps(payload).encode(),
    )

    assert result.source_objects == []
    assert "secret-roadmap.png" not in str(result.model_dump(mode="json"))
    assert "files.slack.com" not in str(result.model_dump(mode="json"))
