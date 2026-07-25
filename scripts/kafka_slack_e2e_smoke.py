from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from sqlalchemy import func, select

from cortex.config import Settings
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.db.models import (
    EmbeddingRecordRecord,
    RawEventRecord,
    SourceChunkRecord,
    SourceObjectRecord,
)
from cortex.db.session import create_sessionmaker
from cortex.events.bus import PIPELINE_TOPICS, KafkaEventBus
from cortex.events.kafka_admin import ensure_pipeline_topics
from cortex.ingestion.durable import SessionRawEventIngestionService
from cortex.ingestion.payloads import FilePayloadStore
from cortex.workers.factory import create_kafka_pipeline_consumer

MESSAGE_TEXT = "Kafka durable smoke retrieval marker"
SMOKE_RUN_ID = os.getenv("CORTEX_SMOKE_ID", str(int(datetime.now(UTC).timestamp())))
WORKSPACE_ID = f"ws_kafka_smoke_{SMOKE_RUN_ID}"
CHANNEL_ID = "C_KAFKA_SMOKE"
SIGNING_SECRET = "smoke-signing-secret"


@dataclass(frozen=True)
class Counts:
    raw_events: int
    source_objects: int
    source_chunks: int
    embeddings: int


async def main() -> int:
    settings = Settings(
        cortex_event_bus="kafka",
        cortex_state_backend="sql",
        cortex_slack_connector_enabled=True,
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex",
        ),
        payload_store_path=os.getenv(
            "PAYLOAD_STORE_PATH", ".local/kafka-smoke-payloads"
        ),
        kafka_consumer_group=f"cortex-smoke-{int(datetime.now(UTC).timestamp())}",
    )
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is required")

    payload_path = Path(settings.payload_store_path)
    payload_path.mkdir(parents=True, exist_ok=True)
    session_factory = create_sessionmaker(settings.database_url)
    await ensure_pipeline_topics(bootstrap_servers=settings.kafka_bootstrap_servers)

    event_bus = KafkaEventBus(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id="cortex-smoke-api",
    )
    ingestion = SessionRawEventIngestionService(
        session_factory=session_factory,
        payload_store=FilePayloadStore(payload_path),
        event_bus=event_bus,
    )
    services = create_slack_connector_services(
        signing_secret=SIGNING_SECRET,
        event_bus=event_bus,
        payload_store=FilePayloadStore(payload_path),
        ingestion_service=ingestion,
        auto_drain_pipeline=False,
    )
    consumer = create_kafka_pipeline_consumer(
        settings=settings,
        session_factory=session_factory,
    )
    await consumer.start(PIPELINE_TOPICS)
    try:
        if consumer.consumer is None:
            raise RuntimeError("Kafka consumer did not start")
        await consumer.consumer.seek_to_end()
        await _select_channel(services)
        webhook_result = await _send_signed_slack_event(services)
        if not webhook_result.raw_event_created:
            raise RuntimeError(f"expected new raw event, got {webhook_result.status}")
        await event_bus.stop()
        seen_payload_text = await _consume_until_complete(
            consumer=consumer,
            session_factory=session_factory,
            timeout_seconds=30,
        )
    finally:
        await event_bus.stop()
        await consumer.stop()

    if MESSAGE_TEXT in seen_payload_text:
        raise RuntimeError("Kafka payload leaked Slack message text")

    counts = await _counts(session_factory)
    print(
        json.dumps(
            {
                "ok": True,
                "counts": counts.__dict__,
                "workspace_id": WORKSPACE_ID,
                "channel_id": CHANNEL_ID,
            },
            sort_keys=True,
        )
    )
    return 0


async def _select_channel(services) -> None:
    start = services.oauth.start_install(workspace_id=WORKSPACE_ID)
    complete = await services.oauth.complete_install(
        code="smoke_oauth_code",
        state=str(start["state"]),
    )
    if not complete["ok"]:
        raise RuntimeError(f"oauth setup failed: {complete}")
    services.sources.select_channels(
        workspace_id=WORKSPACE_ID,
        oauth_installation_id=str(complete["installation"]["id"]),
        channels=[{"id": CHANNEL_ID, "name": "smoke-private-channel"}],
    )


async def _send_signed_slack_event(services):
    body = {
        "team_id": "T_KAFKA_SMOKE",
        "event_id": f"EvKafkaSmoke{int(datetime.now(UTC).timestamp())}",
        "event_time": int(datetime.now(UTC).timestamp()),
        "event": {
            "type": "message",
            "channel": CHANNEL_ID,
            "user": "U_KAFKA_SMOKE",
            "ts": f"{int(datetime.now(UTC).timestamp())}.000100",
            "text": MESSAGE_TEXT,
        },
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    timestamp = str(int(datetime.now(UTC).timestamp()))
    base = b"v0:" + timestamp.encode() + b":" + raw
    signature = (
        "v0=" + hmac.new(SIGNING_SECRET.encode(), base, hashlib.sha256).hexdigest()
    )
    result = await services.webhooks.handle(
        workspace_id=WORKSPACE_ID,
        body=raw,
        timestamp=timestamp,
        signature=signature,
    )
    if not result.ok:
        raise RuntimeError(f"webhook failed: {result.error}")
    return result


async def _consume_until_complete(
    *,
    consumer,
    session_factory,
    timeout_seconds: int,
) -> str:
    deadline = monotonic() + timeout_seconds
    payload_text = ""
    while monotonic() < deadline:
        message = await asyncio.wait_for(consumer.consumer.getone(), timeout=5)
        payload_text += message.value.decode("utf-8", errors="replace")
        result = await consumer.handle_message(message)
        if result.status != "processed":
            raise RuntimeError(f"message was not processed: {result}")
        counts = await _counts(session_factory)
        if (
            counts.raw_events >= 1
            and counts.source_objects >= 1
            and counts.source_chunks >= 1
            and counts.embeddings >= 1
        ):
            return payload_text
    raise TimeoutError("timed out waiting for Kafka pipeline completion")


async def _counts(session_factory) -> Counts:
    async with session_factory() as session:
        raw_events = await session.scalar(
            select(func.count())
            .select_from(RawEventRecord)
            .where(RawEventRecord.workspace_id == WORKSPACE_ID)
        )
        source_objects = await session.scalar(
            select(func.count())
            .select_from(SourceObjectRecord)
            .where(SourceObjectRecord.workspace_id == WORKSPACE_ID)
        )
        source_chunks = await session.scalar(
            select(func.count())
            .select_from(SourceChunkRecord)
            .where(SourceChunkRecord.workspace_id == WORKSPACE_ID)
        )
        embeddings = await session.scalar(
            select(func.count())
            .select_from(EmbeddingRecordRecord)
            .where(EmbeddingRecordRecord.workspace_id == WORKSPACE_ID)
        )
    return Counts(
        raw_events=int(raw_events or 0),
        source_objects=int(source_objects or 0),
        source_chunks=int(source_chunks or 0),
        embeddings=int(embeddings or 0),
    )


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(error),
                    "error_type": type(error).__name__,
                },
                sort_keys=True,
            )
        )
        raise SystemExit(1) from error
