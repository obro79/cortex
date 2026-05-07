import pytest

from cortex.context_gate.repositories import (
    InMemoryContextGateResultRepository,
    InvalidContextGateTransition,
)
from cortex.contracts.enums import ContextGateStatus


def test_context_gate_repository_lifecycle_and_version() -> None:
    repo = InMemoryContextGateResultRepository()
    evaluating = repo.create_evaluating(
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        evidence_pack_id="ep_1",
        gate_version="gate-v1",
    )

    result = repo.complete(
        evaluating.id,
        status=ContextGateStatus.BLOCK,
        risk_category="architecture_conflict",
        reasons_json={"items": [{"message": "conflict", "citation_ids": ["cite-1"]}]},
        required_actions_json={"actions": ["approve", "stop"]},
    )
    resolved = repo.resolve(result.id, action="approve")

    assert result.gate_version == "gate-v1"
    assert result.retrieval_request_id == "ret_1"
    assert result.evidence_pack_id == "ep_1"
    assert resolved.status == ContextGateStatus.BLOCK
    assert resolved.resolved_at is not None
    assert resolved.resolution_action == "approve"
    assert "source_object_id" not in str(result.reasons_json)


def test_context_gate_repository_rejects_invalid_transition() -> None:
    repo = InMemoryContextGateResultRepository()
    evaluating = repo.create_evaluating(
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        evidence_pack_id="ep_1",
        gate_version="gate-v1",
    )
    result = repo.complete(
        evaluating.id,
        status=ContextGateStatus.ALLOW,
        risk_category="clear_context",
        reasons_json={"items": []},
        required_actions_json={"actions": []},
    )

    with pytest.raises(InvalidContextGateTransition):
        repo.resolve(result.id, action="approve")
