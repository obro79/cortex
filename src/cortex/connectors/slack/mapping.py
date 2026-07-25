from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cortex.contracts.entities import SourceConnection
from cortex.ingestion.raw_events import RawEventInput


def slack_message_to_raw_event(
    *,
    workspace_id: str,
    source: SourceConnection,
    message: dict[str, Any],
    event_type: str = "message",
) -> RawEventInput:
    channel_id = source.external_source_id
    message_ts = str(message.get("ts", ""))
    thread_ts = str(message.get("thread_ts") or message_ts)
    subtype = str(message.get("subtype") or event_type)
    provider_event_id = f"{channel_id}:{message_ts}:{subtype}"
    return RawEventInput(
        workspace_id=workspace_id,
        source_connection_id=source.id,
        provider="slack",
        external_event_id=provider_event_id,
        event_type=event_type,
        external_object_key=f"slack:team:{channel_id}:{thread_ts}",
        idempotency_key=f"slack:{workspace_id}:{provider_event_id}",
        payload={
            "event": _safe_message_payload(message),
            "source": {
                "channel_id": channel_id,
                "source_connection_id": source.id,
            },
        },
        occurred_at=_slack_ts_to_datetime(message_ts),
    )


def slack_file_to_raw_event(
    *,
    workspace_id: str,
    source: SourceConnection,
    message: dict[str, Any],
    file: dict[str, Any],
) -> RawEventInput:
    channel_id = source.external_source_id
    message_ts = str(message.get("ts", ""))
    file_id = str(file.get("id", ""))
    return RawEventInput(
        workspace_id=workspace_id,
        source_connection_id=source.id,
        provider="slack",
        external_event_id=f"{channel_id}:{message_ts}:file:{file_id}",
        event_type="file_shared",
        external_object_key=f"slack:team:{channel_id}:{message_ts}:file:{file_id}",
        idempotency_key=f"slack:{workspace_id}:{channel_id}:{message_ts}:file:{file_id}",
        payload={
            "event": {
                "type": "file_shared",
                "channel": channel_id,
                "message_ts": message_ts,
                "file": _safe_file_metadata(file),
            }
        },
        occurred_at=_slack_ts_to_datetime(message_ts),
    )


def slack_link_to_raw_event(
    *,
    workspace_id: str,
    source: SourceConnection,
    message: dict[str, Any],
    link: dict[str, Any],
    index: int,
) -> RawEventInput:
    channel_id = source.external_source_id
    message_ts = str(message.get("ts", ""))
    return RawEventInput(
        workspace_id=workspace_id,
        source_connection_id=source.id,
        provider="slack",
        external_event_id=f"{channel_id}:{message_ts}:link:{index}",
        event_type="link_shared",
        external_object_key=f"slack:team:{channel_id}:{message_ts}:link:{index}",
        idempotency_key=f"slack:{workspace_id}:{channel_id}:{message_ts}:link:{index}",
        payload={
            "event": {
                "type": "link_shared",
                "channel": channel_id,
                "message_ts": message_ts,
                "link": {
                    "domain": link.get("domain"),
                    "url_hash": link.get("url_hash"),
                },
            }
        },
        occurred_at=_slack_ts_to_datetime(message_ts),
    )


def derived_raw_events_for_message(
    *,
    workspace_id: str,
    source: SourceConnection,
    message: dict[str, Any],
) -> list[RawEventInput]:
    events = [
        slack_message_to_raw_event(
            workspace_id=workspace_id, source=source, message=message
        )
    ]
    files = message.get("files", [])
    if isinstance(files, list):
        for file in files:
            if isinstance(file, dict):
                events.append(
                    slack_file_to_raw_event(
                        workspace_id=workspace_id,
                        source=source,
                        message=message,
                        file=file,
                    )
                )
    links = message.get("links", [])
    if isinstance(links, list):
        for index, link in enumerate(links):
            if isinstance(link, dict):
                events.append(
                    slack_link_to_raw_event(
                        workspace_id=workspace_id,
                        source=source,
                        message=message,
                        link=link,
                        index=index,
                    )
                )
    return events


def _safe_file_metadata(file: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": file.get("id"),
        "mimetype": file.get("mimetype"),
        "size": file.get("size"),
        "url_private_hash": file.get("url_private_hash"),
    }


def _safe_message_payload(message: dict[str, Any]) -> dict[str, Any]:
    safe = dict(message)
    files = safe.get("files")
    if isinstance(files, list):
        safe["files"] = [
            _safe_file_metadata(file) for file in files if isinstance(file, dict)
        ]
    return safe


def _slack_ts_to_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(float(value), UTC)
    except ValueError:
        return None
