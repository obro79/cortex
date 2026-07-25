from datetime import UTC, datetime

from cortex.context_gate.render import GateMessageRenderer
from cortex.contracts.entities import ContextGateResult
from cortex.contracts.enums import ContextGateStatus


def test_message_renderer_is_compact_cited_and_safe() -> None:
    now = datetime.now(UTC)
    result = ContextGateResult(
        id="gate_1",
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        evidence_pack_id="ep_1",
        status=ContextGateStatus.BLOCK,
        risk_category="architecture_conflict",
        reasons_json={
            "items": [
                {
                    "message": "Retrieved evidence contains conflicting context.",
                    "citation_ids": ["cite-1"],
                }
            ]
        },
        required_actions_json={"actions": ["approve", "stop"]},
        gate_version="gate-v1",
        evaluated_at=now,
        created_at=now,
        updated_at=now,
    )

    text = GateMessageRenderer().render(result)

    assert "context gate: block" in text
    assert "[cite-1]" in text
    assert "source_object_id" not in text
    assert len(text.split()) < 80
