import pytest

from cortex.contracts.enums import RawEventStatus
from cortex.db.models import RawEventRecord
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.raw_events import (
    InMemoryRawEventRepository,
    RawEventInput,
    RawEventTransitionError,
    apply_raw_event_to_record,
    raw_event_from_record,
)


def create_event(
    repository: InMemoryRawEventRepository, raw_event_id: str = "raw_1"
) -> str:
    store = InMemoryPayloadStore()
    stored = store.put_json({"id": raw_event_id})
    event, _created = repository.create_or_get_by_idempotency_key(
        item=RawEventInput(
            workspace_id="ws_1",
            source_connection_id="src_1",
            provider="fixture",
            external_event_id=f"evt_{raw_event_id}",
            event_type="fixture.created",
            external_object_key=f"fixture:{raw_event_id}",
            idempotency_key=f"fixture:{raw_event_id}",
            payload={"id": raw_event_id},
            raw_event_id=raw_event_id,
        ),
        payload_ref=stored.payload_ref,
        payload_hash=stored.payload_hash,
        payload_size_bytes=stored.payload_size_bytes,
    )
    return event.id


def test_invalid_lifecycle_transition_is_rejected() -> None:
    repository = InMemoryRawEventRepository()
    raw_event_id = create_event(repository)

    with pytest.raises(RawEventTransitionError):
        repository.mark_processed(raw_event_id)


def test_retry_and_deadletter_fields_update() -> None:
    repository = InMemoryRawEventRepository()
    raw_event_id = create_event(repository)

    failed = repository.mark_failed_retryable(raw_event_id, "publish_failed", "boom")
    deadlettered = repository.mark_deadlettered(raw_event_id, "terminal", "stop")

    assert failed.status == RawEventStatus.FAILED_RETRYABLE
    assert failed.attempt_count == 1
    assert deadlettered.status == RawEventStatus.DEADLETTERED
    assert deadlettered.last_error_code == "terminal"


def test_replay_candidates_are_ordered_and_skip_processing_deleted() -> None:
    repository = InMemoryRawEventRepository()
    first = create_event(repository, "raw_1")
    second = create_event(repository, "raw_2")
    third = create_event(repository, "raw_3")

    repository.mark_published(first)
    repository.mark_published(second)
    repository.mark_published(third)
    repository.mark_processing(second)
    repository.mark_processing(third)
    repository.mark_processed(third)
    repository.mark_deleted(third)

    candidates = repository.list_replay_candidates(workspace_id="ws_1")

    assert [event.id for event in candidates] == ["raw_1"]


def test_raw_event_record_mapper_round_trips_status_and_retry_fields() -> None:
    repository = InMemoryRawEventRepository()
    raw_event_id = create_event(repository)
    failed = repository.mark_failed_retryable(raw_event_id, "publish_failed", "boom")
    record = RawEventRecord(
        id=failed.id,
        workspace_id=failed.workspace_id,
        source_connection_id=failed.source_connection_id,
        provider=failed.provider,
        external_event_id=failed.external_event_id,
        event_type=failed.event_type,
        external_object_key=failed.external_object_key,
        idempotency_key=failed.idempotency_key,
        payload_ref=failed.payload_ref,
        payload_hash=failed.payload_hash,
        payload_size_bytes=failed.payload_size_bytes,
        occurred_at=failed.occurred_at,
        received_at=failed.received_at,
        published_at=failed.published_at,
        processed_at=failed.processed_at,
        status=failed.status.value,
        attempt_count=failed.attempt_count,
        last_error_code=failed.last_error_code,
        last_error_message=failed.last_error_message,
        next_retry_at=failed.next_retry_at,
        last_attempt_at=failed.last_attempt_at,
        trace_id=failed.trace_id,
        created_at=failed.created_at,
        updated_at=failed.updated_at,
    )

    round_tripped = raw_event_from_record(record)

    assert round_tripped.status == RawEventStatus.FAILED_RETRYABLE
    assert round_tripped.attempt_count == 1
    assert round_tripped.payload_hash == failed.payload_hash

    processed = repository.mark_processing(raw_event_id)
    processed = repository.mark_processed(processed.id)
    apply_raw_event_to_record(processed, record)

    assert record.status == RawEventStatus.PROCESSED.value
    assert record.processed_at == processed.processed_at
    assert record.payload_ref == failed.payload_ref
