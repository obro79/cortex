from datetime import UTC, datetime, timedelta

import pytest

from cortex.contracts.enums import RawEventStatus
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.events.retry import RetryPolicy
from cortex.ingestion.outbox import (
    OUTBOX_DEADLETTERED,
    OUTBOX_PENDING,
    OUTBOX_PUBLISHED,
    InMemoryOutboxRepository,
    RawEventOutboxDispatcher,
)
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput


def envelope(raw_event_id: str = "raw_1") -> PipelineEventEnvelope:
    return PipelineEventEnvelope(
        event_id=f"evt_{raw_event_id}",
        event_type="raw_event.persisted",
        occurred_at=datetime.now(UTC),
        workspace_id="ws_1",
        partition_key="ws_1:fixture:raw_1",
        subject={"type": "raw_event", "id": raw_event_id},
        trace={"trace_id": "trace_1"},
    )


class RecordingBus:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.events: list[PipelineEventEnvelope] = []

    async def publish(self, event: PipelineEventEnvelope) -> None:
        if self.fail:
            raise RuntimeError("broker unavailable")
        self.events.append(event)


def persisted_raw_event(repository: InMemoryRawEventRepository) -> str:
    stored = InMemoryPayloadStore().put_json({"id": "raw_1"})
    event, created = repository.create_or_get_by_idempotency_key(
        item=RawEventInput(
            workspace_id="ws_1",
            source_connection_id="src_1",
            provider="fixture",
            external_event_id="evt_1",
            event_type="fixture.created",
            external_object_key="fixture:raw_1",
            idempotency_key="fixture:raw_1",
            payload={"id": "raw_1"},
            raw_event_id="raw_1",
        ),
        payload_ref=stored.payload_ref,
        payload_hash=stored.payload_hash,
        payload_size_bytes=stored.payload_size_bytes,
    )
    assert created is True
    return event.id


async def test_enqueue_is_idempotent_and_due_respects_retry_schedule() -> None:
    repository = InMemoryOutboxRepository()
    first = await repository.enqueue(raw_event_id="raw_1", event=envelope())
    duplicate = await repository.enqueue(raw_event_id="raw_1", event=envelope())

    assert duplicate == first
    assert await repository.due(limit=10) == [first]

    failed = await repository.record_failure(first.id, RuntimeError("temporary"))

    assert failed.status == OUTBOX_PENDING
    assert failed.next_attempt_at is not None
    assert (
        await repository.due(
            limit=10, now=failed.next_attempt_at - timedelta(microseconds=1)
        )
        == []
    )
    assert await repository.due(limit=10, now=failed.next_attempt_at) == [failed]


async def test_dispatcher_marks_published_and_reconciles_raw_event() -> None:
    outbox = InMemoryOutboxRepository()
    raw_events = InMemoryRawEventRepository()
    raw_event_id = persisted_raw_event(raw_events)
    message = await outbox.enqueue(
        raw_event_id=raw_event_id, event=envelope(raw_event_id)
    )
    bus = RecordingBus()

    delivered = await RawEventOutboxDispatcher(outbox, bus, raw_events).dispatch_due()

    assert delivered[0].id == message.id
    assert delivered[0].status == OUTBOX_PUBLISHED
    assert raw_events.get_by_id(raw_event_id).status == RawEventStatus.PUBLISHED
    assert bus.events == [message.event]


async def test_dispatcher_reconciles_retry_then_deadletter_in_memory() -> None:
    outbox = InMemoryOutboxRepository(
        RetryPolicy(
            max_attempts=2,
            initial_delay=timedelta(microseconds=1),
            max_delay=timedelta(microseconds=1),
        )
    )
    raw_events = InMemoryRawEventRepository()
    raw_event_id = persisted_raw_event(raw_events)
    message = await outbox.enqueue(
        raw_event_id=raw_event_id, event=envelope(raw_event_id)
    )
    dispatcher = RawEventOutboxDispatcher(outbox, RecordingBus(fail=True), raw_events)

    assert await dispatcher.dispatch_due() == []
    retrying = outbox.get_by_raw_event_id(raw_event_id)
    assert retrying is not None
    assert retrying.status == OUTBOX_PENDING
    assert raw_events.get_by_id(raw_event_id).status == RawEventStatus.FAILED_RETRYABLE

    await dispatcher.dispatch_due()
    deadlettered = outbox.get_by_raw_event_id(raw_event_id)
    assert deadlettered is not None
    assert deadlettered.id == message.id
    assert deadlettered.status == OUTBOX_DEADLETTERED
    assert deadlettered.attempt_count == 2
    assert raw_events.get_by_id(raw_event_id).status == RawEventStatus.DEADLETTERED


async def test_due_requires_positive_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        await InMemoryOutboxRepository().due(limit=0)
