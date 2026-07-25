from datetime import UTC, datetime

from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.events.in_memory import InMemoryEventBus


async def test_in_memory_event_bus_records_events() -> None:
    bus = InMemoryEventBus()
    event = PipelineEventEnvelope(
        event_id="evt_1",
        event_type="raw_event.persisted",
        occurred_at=datetime.now(UTC),
        published_at=datetime.now(UTC),
        workspace_id="ws_1",
        partition_key="ws_1:fixture:1",
        subject={"type": "raw_event", "id": "raw_1"},
        trace={"trace_id": "trace_1"},
    )
    await bus.publish(event)
    assert bus.list_events() == [event]
