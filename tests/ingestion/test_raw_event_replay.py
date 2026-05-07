from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.replay import RawEventReplayService
from cortex.ingestion.service import RawEventIngestionService


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


async def test_replay_by_id_creates_new_envelope_preserving_subject_and_hash() -> None:
    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    publisher = RawEventPublisher(event_bus)
    ingestion = RawEventIngestionService(repository, payload_store, publisher)
    await ingestion.ingest(raw_input())
    original = event_bus.list_events()[0]

    replayed = await RawEventReplayService(repository, publisher).replay_by_id(
        "raw_fixture_1",
        replay_run_id="replay_1",
        replay_reason="manual_test",
        requested_by="tester",
    )

    assert replayed.event_id != original.event_id
    assert replayed.subject.id == original.subject.id
    assert replayed.hashes.payload_hash == original.hashes.payload_hash
    assert replayed.causation.raw_event_id == "raw_fixture_1"
    assert replayed.payload["replay_run_id"] == "replay_1"


async def test_replay_candidates_are_deterministic() -> None:
    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    event_bus = InMemoryEventBus()
    publisher = RawEventPublisher(event_bus)
    ingestion = RawEventIngestionService(repository, payload_store, publisher)
    await ingestion.ingest(raw_input())

    replayed = await RawEventReplayService(repository, publisher).replay_candidates(
        workspace_id="ws_1",
        replay_run_id="replay_2",
        replay_reason="manual",
        requested_by="tester",
    )

    assert [event.subject.id for event in replayed] == ["raw_fixture_1"]
