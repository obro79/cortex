from cortex.canonical_memory.retrieval_priority import CanonicalDecisionCandidateAdapter
from cortex.contracts.enums import ApprovalStatus

from .helpers import make_service, seed_evidence


async def test_only_approved_and_edited_decisions_rank_as_canonical_truth() -> None:
    service, decisions, _approvals, evidence = make_service()
    evidence_pack_id = seed_evidence(evidence)
    approved = service.propose_canonical_decision(
        workspace_id="ws_1",
        evidence_pack_id=evidence_pack_id,
        decision_text="Postgres session storage is canonical.",
    )
    rejected = service.propose_canonical_decision(
        workspace_id="ws_1",
        evidence_pack_id=evidence_pack_id,
        decision_text="Redis session storage is canonical.",
    )
    await service.approve_canonical_decision(
        decision_id=str(approved.result["id"]),
        action="approve",
        actor_id="human_1",
    )
    await service.approve_canonical_decision(
        decision_id=str(rejected.result["id"]),
        action="reject",
        actor_id="human_1",
    )

    active = decisions.list_active("ws_1")
    candidates = CanonicalDecisionCandidateAdapter().candidates_for_query(
        decisions=active, query="session"
    )

    assert [decision.status for decision in active] == [ApprovalStatus.APPROVED]
    assert candidates[0].source_authority_score == 10.0
    assert candidates[0].source_chunk.metadata_json["source_kind"] == (
        "canonical_decision"
    )
