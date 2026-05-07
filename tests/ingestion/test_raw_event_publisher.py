from datetime import UTC, datetime

import pytest

from cortex.contracts.entities import RawEvent
from cortex.contracts.enums import RawEventStatus
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.publisher import RawEventPublisher


def raw_event() -> RawEvent:
    now = datetime.now(UTC)
    return RawEvent(
        id="raw_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider="fixture",
        external_event_id="evt_1",
        event_type="fixture.created",
        external_object_key="fixture:1",
        idempotency_key="fixture:1",
        payload_ref="memory://payloads/1",
        payload_hash="sha256:abc",
        payload_size_bytes=12,
        occurred_at=now,
        received_at=now,
        status=RawEventStatus.PUBLISHED,
        trace_id="trace_1",
        created_at=now,
        updated_at=now,
    )


async def test_raw_event_persisted_envelope_shape() -> None:
    bus = InMemoryEventBus()
    publisher = RawEventPublisher(bus)

    envelope = await publisher.publish_persisted(raw_event())

    assert envelope.event_type == "raw_event.persisted"
    assert envelope.subject.type == "raw_event"
    assert envelope.subject.id == "raw_1"
    assert envelope.causation.raw_event_id == "raw_1"
    assert envelope.hashes.payload_hash == "sha256:abc"
    assert envelope.partition_key == "ws_1:fixture:1"
    assert envelope.payload == {"provider_event_type": "fixture.created"}
    assert bus.list_events() == [envelope]


def test_forbidden_replay_metadata_is_rejected() -> None:
    publisher = RawEventPublisher(InMemoryEventBus())

    with pytest.raises(ValueError, match="raw_payload"):
        publisher.build_persisted_envelope(
            raw_event(),
            replay_metadata={"raw_payload": "do not send"},
        )


def test_envelope_payload_type_contract_remains_valid() -> None:
    envelope = RawEventPublisher(InMemoryEventBus()).build_persisted_envelope(
        raw_event(),
        replay_metadata={"replay_run_id": "replay_1", "requested_by": "dev"},
    )

    PipelineEventEnvelope.model_validate(envelope.model_dump())
    assert envelope.event_id != "raw_1"
