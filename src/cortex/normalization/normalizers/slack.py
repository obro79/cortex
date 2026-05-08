from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from cortex.contracts.entities import RawEvent, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.normalization.normalizers.fixtures import stable_id
from cortex.normalization.result import NormalizationResult

NORMALIZED_VERSION = "slack-normalizer-v1"
SUPPORTED_MESSAGE_TYPES = {"message"}


class SlackNormalizationError(Exception):
    pass


def normalize_slack_payload(
    raw_event: RawEvent, payload_bytes: bytes
) -> NormalizationResult:
    payload = _load_payload(payload_bytes)
    event = payload.get("event")
    if not isinstance(event, dict):
        raise SlackNormalizationError("slack payload missing event object")

    if str(event.get("type", "")) not in SUPPORTED_MESSAGE_TYPES:
        return _empty_result(raw_event)

    text = _optional_str(event.get("text"))
    if not text:
        return _empty_result(raw_event)

    channel_id = _channel_id(raw_event, payload, event)
    message_ts = _required_str(event, "ts")
    thread_ts = _optional_str(event.get("thread_ts")) or message_ts
    team_id = _team_id(raw_event, payload)
    external_object_id = f"{team_id}:{channel_id}:{thread_ts}:{message_ts}"
    external_object_key = f"slack:{external_object_id}"
    now = datetime.now(UTC)
    occurred_at = _slack_ts_to_datetime(message_ts) or raw_event.occurred_at
    source_object = SourceObject(
        id=stable_id(
            "so",
            raw_event.workspace_id,
            "slack",
            "slack_thread",
            external_object_id,
        ),
        workspace_id=raw_event.workspace_id,
        source_connection_id=raw_event.source_connection_id,
        provider="slack",
        object_type="slack_thread",
        external_object_id=external_object_id,
        external_object_key=external_object_key,
        title="Slack thread",
        canonical_url=None,
        author_external_id=_optional_str(event.get("user")),
        occurred_at=occurred_at,
        source_updated_at=_source_updated_at(event) or occurred_at,
        normalized_version=NORMALIZED_VERSION,
        content_hash=sha256_digest(text.encode()),
        content_text=text,
        metadata_json={
            "source_kind": "slack_message",
            "team_id": team_id,
            "channel_id": channel_id,
            "channel_id_hash": sha256_digest(channel_id.encode()),
            "user_id": _optional_str(event.get("user")),
            "message_ts": message_ts,
            "thread_ts": thread_ts,
            "is_thread_reply": thread_ts != message_ts,
            "reply_count": _safe_int(event.get("reply_count")),
            "file_count": _count_items(event.get("files")),
            "link_count": _count_items(event.get("links")),
            "has_files": _count_items(event.get("files")) > 0,
            "has_links": _count_items(event.get("links")) > 0,
        },
        status=SourceObjectStatus.ACTIVE,
        trace_id=raw_event.trace_id,
        created_at=now,
        updated_at=now,
    )
    return NormalizationResult(
        raw_event_id=raw_event.id,
        normalized_version=NORMALIZED_VERSION,
        source_objects=[source_object],
        source_files=[],
        relationship_seeds=[],
    )


def _empty_result(raw_event: RawEvent) -> NormalizationResult:
    return NormalizationResult(
        raw_event_id=raw_event.id,
        normalized_version=NORMALIZED_VERSION,
        source_objects=[],
        source_files=[],
        relationship_seeds=[],
    )


def _load_payload(payload_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as error:
        raise SlackNormalizationError("slack payload is not valid JSON") from error
    if not isinstance(payload, dict):
        raise SlackNormalizationError("slack payload must be a JSON object")
    return payload


def _channel_id(
    raw_event: RawEvent, payload: dict[str, Any], event: dict[str, Any]
) -> str:
    source = payload.get("source")
    if isinstance(source, dict):
        channel = _optional_str(source.get("channel_id"))
        if channel:
            return channel
    channel = _optional_str(event.get("channel"))
    if channel:
        return channel
    parsed = _parse_external_object_key(raw_event.external_object_key or "")
    if parsed is not None:
        return parsed["channel_id"]
    raise SlackNormalizationError("slack payload missing channel id")


def _team_id(raw_event: RawEvent, payload: dict[str, Any]) -> str:
    for key in ("team_id", "team"):
        value = _optional_str(payload.get(key))
        if value:
            return value
    authorizations = payload.get("authorizations")
    if isinstance(authorizations, list):
        for item in authorizations:
            if isinstance(item, dict):
                value = _optional_str(item.get("team_id"))
                if value:
                    return value
    parsed = _parse_external_object_key(raw_event.external_object_key or "")
    if parsed is not None:
        return parsed["team_id"]
    return "team"


def _parse_external_object_key(value: str) -> dict[str, str] | None:
    parts = value.split(":")
    if len(parts) < 4 or parts[0] != "slack":
        return None
    return {
        "team_id": parts[1],
        "channel_id": parts[2],
        "thread_ts": parts[3],
    }


def _source_updated_at(event: dict[str, Any]) -> datetime | None:
    edited = event.get("edited")
    if isinstance(edited, dict):
        edited_ts = _optional_str(edited.get("ts"))
        if edited_ts:
            return _slack_ts_to_datetime(edited_ts)
    return None


def _slack_ts_to_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), UTC)
    except ValueError:
        return None


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = _optional_str(payload.get(key))
    if not value:
        raise SlackNormalizationError(f"slack payload missing string field: {key}")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value if value else None
    return None


def _count_items(value: object) -> int:
    if isinstance(value, list):
        return sum(1 for item in value if isinstance(item, dict))
    return 0


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0
