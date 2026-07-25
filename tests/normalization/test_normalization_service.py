from dataclasses import replace

from cortex.contracts.enums import RawEventStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import RawEventIngestionService
from cortex.normalization.publishers import SourceFilePublisher, SourceObjectPublisher
from cortex.normalization.repositories import (
    InMemoryRelationshipSeedRepository,
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
)
from cortex.normalization.service import SourceNormalizationService


def fixture_payload(
    content: str = "Implement COR-123 from Linear.",
) -> dict[str, object]:
    return {
        "fixture_id": "linear-issue-COR-123",
        "provider": "linear",
        "object_type": "linear_issue",
        "title": "COR-123 migrate session reads to Postgres",
        "canonical_url": "https://fixtures.local/linear/COR-123",
        "content": content,
        "source_kind": "linear_task",
        "relationships": [
            {
                "type": "implemented_by",
                "to_id": "so-github-pr-184",
                "confidence": 0.9,
            }
        ],
    }


def raw_input(payload: dict[str, object] | None = None) -> RawEventInput:
    return RawEventInput(
        workspace_id="ws_1",
        source_connection_id="src_fixture",
        provider="linear",
        external_event_id="evt_linear_1",
        event_type="linear.issue.fixture",
        external_object_key="linear:COR-123",
        idempotency_key="linear:COR-123",
        payload=payload or fixture_payload(),
        trace_id="trace_1",
        raw_event_id="raw_linear_1",
    )


async def create_raw_event(
    raw_events: InMemoryRawEventRepository,
    payload_store: InMemoryPayloadStore,
    event_bus: InMemoryEventBus,
    payload: dict[str, object] | None = None,
):
    ingestion = RawEventIngestionService(
        raw_events,
        payload_store,
        RawEventPublisher(event_bus),
    )
    await ingestion.ingest(raw_input(payload))
    return event_bus.list_events()[0]


def service(
    raw_events: InMemoryRawEventRepository,
    payload_store: InMemoryPayloadStore,
    event_bus: InMemoryEventBus,
) -> tuple[
    SourceNormalizationService,
    InMemorySourceObjectRepository,
    InMemorySourceFileRepository,
    InMemoryRelationshipSeedRepository,
]:
    source_objects = InMemorySourceObjectRepository()
    source_files = InMemorySourceFileRepository()
    relationship_seeds = InMemoryRelationshipSeedRepository()
    return (
        SourceNormalizationService(
            raw_events=raw_events,
            payload_store=payload_store,
            source_objects=source_objects,
            source_files=source_files,
            relationship_seeds=relationship_seeds,
            source_object_publisher=SourceObjectPublisher(event_bus),
            source_file_publisher=SourceFilePublisher(event_bus),
        ),
        source_objects,
        source_files,
        relationship_seeds,
    )


async def test_normalization_persists_then_publishes_source_object_event() -> None:
    raw_events = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    raw_envelope = await create_raw_event(raw_events, payload_store, event_bus)
    normalization, source_objects, _source_files, relationship_seeds = service(
        raw_events, payload_store, event_bus
    )

    result = await normalization.handle_raw_event_persisted(raw_envelope)

    events = event_bus.list_events()
    source_event = events[1]
    raw_event = raw_events.get_by_id("raw_linear_1")
    persisted_source = source_objects.get_by_external_identity(
        "ws_1", "linear", "linear_issue", "linear-issue-COR-123"
    )

    assert result.status == "processed"
    assert result.published_count == 1
    assert raw_event.status == RawEventStatus.PROCESSED
    assert persisted_source is not None
    assert persisted_source.content_hash is not None
    assert len(relationship_seeds.list_all()) == 1
    assert source_event.event_type == "source_object.upserted"
    assert source_event.subject.id == persisted_source.id
    assert source_event.payload["operation"] == "inserted"


async def test_normalization_replay_noops_existing_records_without_republish() -> None:
    raw_events = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    raw_envelope = await create_raw_event(raw_events, payload_store, event_bus)
    normalization, _source_objects, _source_files, _relationship_seeds = service(
        raw_events, payload_store, event_bus
    )

    first = await normalization.handle_raw_event_persisted(raw_envelope)
    second = await normalization.handle_raw_event_persisted(raw_envelope)

    assert first.published_count == 1
    assert second.status == "processed"
    assert second.published_count == 0
    assert [event.event_type for event in event_bus.list_events()] == [
        "raw_event.persisted",
        "source_object.upserted",
    ]


async def test_changed_content_hash_updates_and_republishes() -> None:
    raw_events = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    first_envelope = await create_raw_event(raw_events, payload_store, event_bus)
    normalization, source_objects, _source_files, _relationship_seeds = service(
        raw_events, payload_store, event_bus
    )
    await normalization.handle_raw_event_persisted(first_envelope)
    original = source_objects.get_by_external_identity(
        "ws_1", "linear", "linear_issue", "linear-issue-COR-123"
    )
    second_input = replace(
        raw_input(fixture_payload("Updated Linear content.")),
        external_event_id="evt_linear_2",
        idempotency_key="linear:COR-123:v2",
        raw_event_id="raw_linear_2",
    )
    await RawEventIngestionService(
        raw_events, payload_store, RawEventPublisher(event_bus)
    ).ingest(second_input)
    second_envelope = event_bus.list_events()[-1]

    result = await normalization.handle_raw_event_persisted(second_envelope)
    updated = source_objects.get_by_external_identity(
        "ws_1", "linear", "linear_issue", "linear-issue-COR-123"
    )

    assert result.published_count == 1
    assert updated is not None
    assert original is not None
    assert updated.content_hash != original.content_hash
    assert event_bus.list_events()[-1].payload["operation"] == "updated"


async def test_invalid_payload_marks_retryable_then_deadlettered() -> None:
    raw_events = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    raw_envelope = await create_raw_event(
        raw_events, payload_store, event_bus, {"bad": True}
    )
    normalization, _source_objects, _source_files, _relationship_seeds = service(
        raw_events, payload_store, event_bus
    )
    normalization.max_attempts = 2

    first = await normalization.handle_raw_event_persisted(raw_envelope)
    second = await normalization.handle_raw_event_persisted(raw_envelope)

    assert first.status == "retryable"
    assert second.status == "deadlettered"
    assert raw_events.get_by_id("raw_linear_1").status == RawEventStatus.DEADLETTERED


async def test_normalization_service_ignores_cross_workspace_envelope() -> None:
    raw_events = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    raw_envelope = await create_raw_event(raw_events, payload_store, event_bus)
    normalization, _source_objects, _source_files, _relationship_seeds = service(
        raw_events, payload_store, event_bus
    )

    result = await normalization.handle_raw_event_persisted(
        raw_envelope.model_copy(update={"workspace_id": "ws_other"})
    )

    assert result.status == "ignored"
    assert result.reason == "workspace_mismatch"
    assert raw_events.get_by_id("raw_linear_1").status == RawEventStatus.PUBLISHED


async def test_publish_failure_retries_existing_durable_records() -> None:
    class FailingBus:
        async def publish(self, _event: object) -> None:
            raise RuntimeError("publish failed")

    raw_events = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    raw_envelope = await create_raw_event(raw_events, payload_store, event_bus)
    normalization, source_objects, _source_files, _relationship_seeds = service(
        raw_events, payload_store, event_bus
    )
    normalization.source_object_publisher = SourceObjectPublisher(FailingBus())

    first = await normalization.handle_raw_event_persisted(raw_envelope)
    normalization.source_object_publisher = SourceObjectPublisher(event_bus)
    second = await normalization.handle_raw_event_persisted(raw_envelope)

    persisted_source = source_objects.get_by_external_identity(
        "ws_1", "linear", "linear_issue", "linear-issue-COR-123"
    )
    assert first.status == "retryable"
    assert persisted_source is not None
    assert second.status == "processed"
    assert second.published_count == 1
    assert event_bus.list_events()[-1].event_type == "source_object.upserted"
