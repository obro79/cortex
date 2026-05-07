from cortex.contracts.enums import ApprovalStatus

from .helpers import make_service, seed_evidence


def test_proposal_creates_needs_review_with_citations() -> None:
    service, _decisions, _approvals, evidence = make_service()
    evidence_pack_id = seed_evidence(evidence)

    response = service.propose_canonical_decision(
        workspace_id="ws_1",
        evidence_pack_id=evidence_pack_id,
        scope_type="linear_issue",
        scope_ref="COR-123",
        title="Session storage canonical decision",
        decision_text="Postgres is the future session source of truth.",
        actor_id="agent_1",
    )

    assert response.ok is True
    assert response.result["status"] == ApprovalStatus.NEEDS_REVIEW
    assert response.result["title"] == "Session storage canonical decision"
    assert response.result["source_citations_json"] == {"citation_ids": ["cite-1"]}


def test_proposal_rejects_missing_citations() -> None:
    service, _decisions, _approvals, evidence = make_service()
    pack = evidence.create(
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        claims_json={},
        citations_json={"items": []},
        candidate_summary_json={},
        source_coverage_json={},
        permission_exclusions_json={},
        missing_context_json={},
        stale_context_json={},
        conflict_summary_json={},
        token_budget=4000,
        ranker_version="ranking-v1",
    )

    response = service.propose_canonical_decision(
        workspace_id="ws_1", evidence_pack_id=pack.id
    )

    assert response.ok is False
    assert response.error == "missing_citations"
