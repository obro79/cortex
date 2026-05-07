from datetime import UTC, datetime

from cortex.canonical_memory.publishers import CanonicalDecisionPublisher
from cortex.contracts.entities import CanonicalDecision
from cortex.contracts.enums import ApprovalStatus
from cortex.events.in_memory import InMemoryEventBus


async def test_canonical_decision_approved_event_is_pointer_only() -> None:
    now = datetime.now(UTC)
    decision = CanonicalDecision(
        id="cd_1",
        workspace_id="ws_1",
        scope_type="linear_issue",
        scope_ref="COR-123",
        title="Session storage canonical decision",
        decision_text="secret customer decision text",
        status=ApprovalStatus.APPROVED,
        evidence_pack_id="ep_1",
        approved_by_actor_id="human_1",
        approved_at=now,
        source_citations_json={"citation_ids": ["cite-1"]},
        stale_or_superseded_evidence_json={},
        decision_version="canonical-decision-v1",
        created_at=now,
        updated_at=now,
    )

    envelope = await CanonicalDecisionPublisher(InMemoryEventBus()).publish_approved(
        decision, action="approve"
    )

    assert envelope.event_type == "canonical_decision.approved"
    assert envelope.subject.type == "canonical_decision"
    assert envelope.payload == {
        "action": "approve",
        "status": "approved",
        "scope_type": "linear_issue",
        "operation": "approved",
    }
    assert "decision_text" not in envelope.payload
