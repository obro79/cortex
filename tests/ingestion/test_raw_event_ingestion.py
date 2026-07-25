import pytest

from cortex.contracts.enums import RawEventStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import (
    InMemoryRawEventRepository,
    RawEventIdempotencyConflict,
    RawEventInput,
)
from cortex.ingestion.service import RawEventIngestionService


def raw_input(payload: dict[str, object] | None = None) -> RawEventInput:
    return RawEventInput(
        workspace_id="ws_1",
        source_connection_id="src_fixture",
        provider="fixture",
        external_event_id="evt_fixture_1",
        event_type="fixture.created",
        external_object_key="fixture:1",
        idempotency_key="fixture:1",
        payload=payload or {"fixture_id": "one", "small": True},
        trace_id="trace_1",
        raw_event_id="raw_fixture_1",
    )


def service() -> tuple[
    RawEventIngestionService,
    InMemoryRawEventRepository,
    InMemoryPayloadStore,
    InMemoryEventBus,
]:
    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    return (
        RawEventIngestionService(
            repository,
            payload_store,
            RawEventPublisher(event_bus),
        ),
        repository,
        payload_store,
        event_bus,
    )


async def test_ingest_persists_payload_and_publishes_pointer_event() -> None:
    ingestion, repository, payload_store, event_bus = service()

    result = await ingestion.ingest(raw_input())

    raw_event = repository.get_by_id(result.raw_event_id)
    assert result.created is True
    assert result.published is True
    assert raw_event.status == RawEventStatus.PUBLISHED
    assert raw_event.published_at is not None
    assert raw_event.payload_ref is not None
    assert payload_store.get(raw_event.payload_ref)
    assert len(event_bus.list_events()) == 1
    assert "fixture_id" not in event_bus.list_events()[0].payload


async def test_duplicate_same_payload_noops_before_payload_write_or_publish() -> None:
    ingestion, _repository, payload_store, event_bus = service()

    first = await ingestion.ingest(raw_input())
    second = await ingestion.ingest(raw_input())

    assert first.raw_event_id == second.raw_event_id
    assert second.created is False
    assert second.published is False
    assert payload_store.write_count == 1
    assert len(event_bus.list_events()) == 1


async def test_duplicate_idempotency_key_with_different_hash_conflicts() -> None:
    ingestion, repository, payload_store, event_bus = service()
    await ingestion.ingest(raw_input({"version": 1}))

    with pytest.raises(RawEventIdempotencyConflict):
        await ingestion.ingest(raw_input({"version": 2}))

    raw_event = repository.get_by_id("raw_fixture_1")
    assert raw_event.payload_hash is not None
    assert payload_store.write_count == 1
    assert len(event_bus.list_events()) == 1


async def test_publish_failure_marks_retryable() -> None:
    class FailingBus:
        async def publish(self, _event: object) -> None:
            raise RuntimeError("broker unavailable")

    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    ingestion = RawEventIngestionService(
        repository,
        payload_store,
        RawEventPublisher(FailingBus()),
    )

    result = await ingestion.ingest(raw_input())
    raw_event = repository.get_by_id(result.raw_event_id)

    assert result.created is True
    assert result.published is False
    assert raw_event.status == RawEventStatus.FAILED_RETRYABLE
    assert raw_event.attempt_count == 1
    assert raw_event.last_error_code == "publish_failed"
