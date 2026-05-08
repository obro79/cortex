from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.workers.kafka import KafkaPipelineConsumer, RetryablePipelineError


@dataclass(frozen=True)
class Message:
    value: bytes
    topic: str = "pipeline.raw-events"
    partition: int = 0
    offset: int = 1


class FakeConsumer:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bytes, bytes]] = []

    async def send_and_wait(self, topic: str, value: bytes, *, key: bytes) -> None:
        self.sent.append((topic, value, key))


class FakeDispatcher:
    def __init__(self, *, fail: bool = False, retryable: bool = False) -> None:
        self.fail = fail
        self.retryable = retryable
        self.seen: list[str] = []

    async def drain(self, event_bus) -> None:
        self.seen.append(event_bus.events[0].event_type)
        if self.retryable:
            raise RetryablePipelineError("not ready")
        if self.fail:
            raise RuntimeError("boom")


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


async def test_kafka_consumer_dispatches_and_commits_after_success() -> None:
    consumer = FakeConsumer()
    producer = FakeProducer()
    dispatcher = FakeDispatcher()
    worker = KafkaPipelineConsumer(
        bootstrap_servers="localhost:9092",
        group_id="group",
        dispatcher=dispatcher,  # type: ignore[arg-type]
        consumer=consumer,
        producer=producer,
    )

    result = await worker.handle_message(Message(envelope().model_dump_json().encode()))

    assert result.status == "processed"
    assert dispatcher.seen == ["raw_event.persisted"]
    assert consumer.commits == 1
    assert producer.sent == []


async def test_kafka_consumer_deadletters_handler_failures_without_content() -> None:
    consumer = FakeConsumer()
    producer = FakeProducer()
    worker = KafkaPipelineConsumer(
        bootstrap_servers="localhost:9092",
        group_id="group",
        dispatcher=FakeDispatcher(fail=True),  # type: ignore[arg-type]
        consumer=consumer,
        producer=producer,
    )

    result = await worker.handle_message(Message(envelope().model_dump_json().encode()))

    assert result.status == "deadlettered"
    assert consumer.commits == 1
    topic, value, key = producer.sent[0]
    deadletter = PipelineEventEnvelope.model_validate_json(value)
    assert topic == "pipeline.deadletters"
    assert key == b"ws_1:slack:T1:C1:1"
    assert deadletter.payload["error_code"] == "handler_failed"
    assert "raw payload" not in str(deadletter.payload)


async def test_kafka_consumer_does_not_commit_retryable_dispatch() -> None:
    consumer = FakeConsumer()
    producer = FakeProducer()
    worker = KafkaPipelineConsumer(
        bootstrap_servers="localhost:9092",
        group_id="group",
        dispatcher=FakeDispatcher(retryable=True),  # type: ignore[arg-type]
        consumer=consumer,
        producer=producer,
    )

    result = await worker.handle_message(Message(envelope().model_dump_json().encode()))

    assert result.status == "retryable"
    assert result.reason == "not ready"
    assert consumer.commits == 0
    assert producer.sent == []
