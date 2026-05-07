from cortex.contracts.enums import RawEventStatus
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import RawEventIngestionService
from cortex.workers.normalization import NormalizationWorkerSkeleton


def raw_input() -> RawEventInput:
    return RawEventInput(
        workspace_id="ws_1",
        source_connection_id="src_fixture",
        provider="fixture",
        external_event_id="evt_fixture_1",
        event_type="fixture.created",
        external_object_key="fixture:1",
        idempotency_key="fixture:1",
        payload={"fixture_id": "one", "small": True},
        trace_id="trace_1",
        raw_event_id="raw_fixture_1",
    )


async def persisted_envelope(
    repository: InMemoryRawEventRepository,
    payload_store: InMemoryPayloadStore,
    event_bus: InMemoryEventBus,
) -> PipelineEventEnvelope:
    ingestion = RawEventIngestionService(
        repository,
        payload_store,
        RawEventPublisher(event_bus),
    )
    await ingestion.ingest(raw_input())
    return event_bus.list_events()[0]


async def test_normalization_worker_loads_pointer_and_marks_processed() -> None:
    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    envelope = await persisted_envelope(repository, payload_store, event_bus)

    result = await NormalizationWorkerSkeleton(
        repository, payload_store
    ).handle_raw_event_persisted(envelope)

    raw_event = repository.get_by_id("raw_fixture_1")
    assert result["status"] == "processed"
    assert raw_event.status == RawEventStatus.PROCESSED
    assert raw_event.processed_at is not None


async def test_normalization_worker_retry_then_deadletters_missing_payload() -> None:
    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    envelope = await persisted_envelope(repository, payload_store, event_bus)
    raw_event = repository.get_by_id("raw_fixture_1")
    payload_store._payloads.clear()
    worker = NormalizationWorkerSkeleton(repository, payload_store, max_attempts=2)

    first = await worker.handle_raw_event_persisted(envelope)
    second = await worker.handle_raw_event_persisted(envelope)

    assert first["status"] == "retryable"
    assert second["status"] == "deadlettered"
    assert repository.get_by_id(raw_event.id).status == RawEventStatus.DEADLETTERED


async def test_normalization_worker_ignores_unsupported_events() -> None:
    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    envelope = await persisted_envelope(repository, payload_store, event_bus)
    ignored = envelope.model_copy(update={"event_type": "source_object.upserted"})

    result = await NormalizationWorkerSkeleton(
        repository, payload_store
    ).handle_raw_event_persisted(ignored)

    assert result == {"status": "ignored", "reason": "unsupported_event_type"}
