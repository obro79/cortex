from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.events.bus import (
    KafkaEventBus,
    UnsupportedPipelineEventType,
    topic_for_event_type,
)


class FakeProducer:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.sent: list[tuple[str, bytes, bytes, tuple[tuple[str, bytes], ...]]] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_and_wait(
        self,
        topic: str,
        value: bytes,
        *,
        key: bytes,
        headers: tuple[tuple[str, bytes], ...],
    ) -> None:
        self.sent.append((topic, value, key, headers))


def envelope() -> PipelineEventEnvelope:
    return PipelineEventEnvelope(
        event_id="evt_1",
        event_type="raw_event.persisted",
        occurred_at=datetime.now(UTC),
        published_at=datetime.now(UTC),
        workspace_id="ws_1",
        partition_key="ws_1:slack:T1:C1:1",
        subject={"type": "raw_event", "id": "raw_1"},
        trace={"trace_id": "trace_1"},
    )


def test_topic_mapping_rejects_unknown_event_type() -> None:
    assert topic_for_event_type("raw_event.persisted") == "pipeline.raw-events"
    with pytest.raises(UnsupportedPipelineEventType):
        topic_for_event_type("unknown.event")


async def test_kafka_event_bus_publishes_json_with_partition_key() -> None:
    producer = FakeProducer()
    event = envelope()
    bus = KafkaEventBus(bootstrap_servers="localhost:9092", producer=producer)

    await bus.publish(event)

    assert producer.started is True
    topic, value, key, headers = producer.sent[0]
    assert topic == "pipeline.raw-events"
    assert key == b"ws_1:slack:T1:C1:1"
    assert PipelineEventEnvelope.model_validate_json(value).event_id == "evt_1"
    assert ("event_id", b"evt_1") in headers
