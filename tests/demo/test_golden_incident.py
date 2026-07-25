from cortex.demo.golden_incident import (
    expected_counts,
    load_golden_incident_manifest,
)
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository
from cortex.ingestion.service import RawEventIngestionService
from cortex.normalization.registry import NormalizerRegistry


def test_golden_incident_manifest_freezes_expected_corpus() -> None:
    manifest = load_golden_incident_manifest()

    assert manifest.workspace_id == "ws_demo_cor_123"
    assert manifest.task_ref == "COR-123"
    assert expected_counts(manifest).__dict__ == {
        "records": 18,
        "decisive": 6,
        "distractors": 12,
        "pre_live": 17,
        "live_transition": 1,
        "providers": 6,
    }
    assert manifest.sha256.startswith("sha256:")


def test_golden_incident_enters_only_through_raw_event_inputs() -> None:
    manifest = load_golden_incident_manifest()
    inputs = (*manifest.pre_live_inputs(), manifest.live_input())

    assert len(inputs) == 18
    assert len({item.idempotency_key for item in inputs}) == 18
    assert all(item.workspace_id == "ws_demo_cor_123" for item in inputs)
    assert all(item.payload["synthetic_demo"] is True for item in inputs)
    assert all(item.payload["manifest_sha256"] == manifest.sha256 for item in inputs)
    assert all(item.payload["provider"] == item.provider for item in inputs)
    assert manifest.live_input().provider == "slack"
    assert manifest.live_input().payload["mode"] == "simulated_fallback"
    assert manifest.live_input().event_type.endswith(".demo_simulated")


async def test_all_golden_inputs_validate_and_normalize_with_provider_labels() -> None:
    manifest = load_golden_incident_manifest()
    repository = InMemoryRawEventRepository()
    payload_store = InMemoryPayloadStore()
    ingestion = RawEventIngestionService(
        repository,
        payload_store,
        RawEventPublisher(InMemoryEventBus()),
    )
    registry = NormalizerRegistry()

    inputs = (*manifest.pre_live_inputs(), manifest.live_input())
    normalized = []
    for item in inputs:
        result = await ingestion.ingest(item)
        raw_event = repository.get_by_id(result.raw_event_id)
        normalized.append(
            registry.resolve(raw_event)(
                raw_event, payload_store.get(raw_event.payload_ref or "")
            )
        )

    source_objects = [result.source_objects[0] for result in normalized]
    assert {source_object.provider for source_object in source_objects} == {
        "slack",
        "github",
        "jira",
        "email",
        "google_drive",
        "agent_session",
    }
    assert all(
        source_object.metadata_json["synthetic_demo"] is True
        for source_object in source_objects
    )
