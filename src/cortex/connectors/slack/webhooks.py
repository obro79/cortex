from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from cortex.ingestion.raw_events import RawEventInput
from cortex.ingestion.service import IngestionResult
from cortex.utils.asyncio import maybe_await

SUPPORTED_EVENT_TYPES = {"message", "file_shared", "link_shared"}


@dataclass(frozen=True)
class SlackWebhookResult:
    ok: bool
    status: str
    raw_event_created: bool = False
    challenge: str | None = None
    error: str | None = None


class SlackWebhookVerifier:
    def __init__(self, signing_secret: str, *, tolerance_seconds: int = 300) -> None:
        self.signing_secret = signing_secret
        self.tolerance_seconds = tolerance_seconds

    def verify(self, *, timestamp: str, body: bytes, signature: str) -> bool:
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        if abs(int(datetime.now(UTC).timestamp()) - ts) > self.tolerance_seconds:
            return False
        base = b"v0:" + timestamp.encode() + b":" + body
        digest = hmac.new(
            self.signing_secret.encode(), base, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"v0={digest}", signature)


class SlackWebhookIngestionService(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


class SlackWebhookService:
    def __init__(
        self,
        *,
        deliveries: Any,
        installations: Any,
        source_connections: Any,
        ingestion: SlackWebhookIngestionService,
        verifier: SlackWebhookVerifier,
    ) -> None:
        self.deliveries = deliveries
        self.installations = installations
        self.source_connections = source_connections
        self.ingestion = ingestion
        self.verifier = verifier

    async def handle(
        self,
        *,
        workspace_id: str,
        body: bytes,
        timestamp: str,
        signature: str,
        retry_num: str | None = None,
    ) -> SlackWebhookResult:
        if not self.verifier.verify(
            timestamp=timestamp, body=body, signature=signature
        ):
            return SlackWebhookResult(ok=False, status="failed", error="bad_signature")
        payload = json.loads(body.decode())
        if payload.get("type") == "url_verification":
            return SlackWebhookResult(
                ok=True, status="verified", challenge=str(payload.get("challenge", ""))
            )
        event = payload.get("event", {})
        if not isinstance(event, dict):
            return SlackWebhookResult(ok=True, status="ignored")
        slack_team_id = str(
            payload.get("context_team_id")
            or payload.get("team_id")
            or event.get("team")
            or ""
        )
        installation = (
            await maybe_await(
                self.installations.get_active_by_provider_workspace_id(slack_team_id)
            )
            if slack_team_id
            else None
        )
        resolved_workspace_id = (
            installation.workspace_id if installation else workspace_id
        )
        event_id = str(payload.get("event_id") or event.get("client_msg_id") or "")
        delivery_id = str(
            payload.get("event_id")
            or f"{event.get('channel')}:{event.get('ts')}:{retry_num or '0'}"
        )
        delivery, created = await maybe_await(
            self.deliveries.create_or_duplicate(
                workspace_id=resolved_workspace_id,
                delivery_id=delivery_id,
                event_id=event_id or None,
                signature_status="verified",
            )
        )
        if not created:
            return SlackWebhookResult(ok=True, status=str(delivery.status))
        event_type = str(event.get("type", ""))
        if event_type not in SUPPORTED_EVENT_TYPES:
            return SlackWebhookResult(ok=True, status="ignored")
        channel_id = str(event.get("channel", ""))
        source = await maybe_await(
            self.source_connections.get_selected_channel(
                resolved_workspace_id, channel_id
            )
        )
        if source is None:
            return SlackWebhookResult(ok=True, status="ignored_unselected")
        event_ts = str(event.get("ts") or payload.get("event_time") or "")
        thread_ts = str(event.get("thread_ts") or event_ts)
        team_id = str(
            source.provider_metadata_json.get("team_id") or slack_team_id or "team"
        )
        result = await self.ingestion.ingest(
            RawEventInput(
                workspace_id=resolved_workspace_id,
                source_connection_id=source.id,
                provider="slack",
                external_event_id=event_id or f"{channel_id}:{event_ts}",
                event_type=event_type,
                external_object_key=f"slack:{team_id}:{channel_id}:{thread_ts}",
                idempotency_key=f"slack:{resolved_workspace_id}:{channel_id}:{event_ts}:{event_type}",
                payload=payload,
                occurred_at=datetime.fromtimestamp(
                    int(payload.get("event_time", datetime.now(UTC).timestamp())),
                    UTC,
                ),
            )
        )
        await maybe_await(
            self.deliveries.mark_persisted(
                delivery.id,
                source_connection_id=source.id,
                raw_event_id=result.raw_event_id,
            )
        )
        return SlackWebhookResult(
            ok=True,
            status="persisted",
            raw_event_created=result.created,
        )
