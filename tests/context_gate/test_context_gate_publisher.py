from datetime import UTC, datetime

from cortex.context_gate.publishers import ContextGatePublisher
from cortex.contracts.entities import ContextGateResult
from cortex.contracts.enums import ContextGateStatus
from cortex.events.in_memory import InMemoryEventBus


async def test_context_gate_completed_envelope_is_pointer_only() -> None:
    now = datetime.now(UTC)
    result = ContextGateResult(
        id="gate_1",
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        evidence_pack_id="ep_1",
        status=ContextGateStatus.BLOCK,
        risk_category="architecture_conflict",
        reasons_json={"items": [{"message": "secret snippet"}]},
        required_actions_json={"actions": ["approve", "stop"]},
        gate_version="gate-v1",
        evaluated_at=now,
        created_at=now,
        updated_at=now,
    )

    envelope = await ContextGatePublisher(InMemoryEventBus()).publish_completed(result)

    assert envelope.event_type == "context_gate.completed"
    assert envelope.subject.type == "context_gate_result"
    assert envelope.causation.retrieval_request_id == "ret_1"
    assert envelope.versions.gate_version == "gate-v1"
    assert envelope.payload == {
        "status": "block",
        "risk_category": "architecture_conflict",
        "operation": "completed",
    }
