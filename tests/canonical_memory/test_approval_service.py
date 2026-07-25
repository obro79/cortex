from cortex.contracts.enums import ApprovalStatus

from .helpers import make_service, seed_evidence


def propose_decision() -> tuple[object, str]:
    service, _decisions, _approvals, evidence = make_service()
    evidence_pack_id = seed_evidence(evidence)
    proposal = service.propose_canonical_decision(
        workspace_id="ws_1",
        evidence_pack_id=evidence_pack_id,
        scope_ref="COR-123",
        decision_text="Postgres is canonical for sessions.",
    )
    return service, str(proposal.result["id"])


async def test_approve_requires_human_actor() -> None:
    service, decision_id = propose_decision()

    missing = await service.approve_canonical_decision(
        decision_id=decision_id, action="approve", actor_id=None
    )
    agent = await service.approve_canonical_decision(
        decision_id=decision_id, action="approve", actor_id="agent_1"
    )

    assert missing.error == "human_actor_required"
    assert agent.error == "human_actor_required"


async def test_approve_preserves_proposal_text_and_records_audit() -> None:
    service, decision_id = propose_decision()

    response = await service.approve_canonical_decision(
        decision_id=decision_id, action="approve", actor_id="human_1"
    )

    decision = response.result["decision"]
    approval = response.result["approval_record"]
    assert decision["status"] == ApprovalStatus.APPROVED
    assert decision["approved_by_actor_id"] == "human_1"
    assert approval["original_text"] == "Postgres is canonical for sessions."
    assert approval["final_text"] == "Postgres is canonical for sessions."


async def test_edit_requires_and_persists_final_text() -> None:
    service, decision_id = propose_decision()

    missing = await service.approve_canonical_decision(
        decision_id=decision_id, action="edit", actor_id="human_1"
    )
    edited = await service.approve_canonical_decision(
        decision_id=decision_id,
        action="edit",
        actor_id="human_1",
        final_text="Postgres is canonical; Redis fallback remains until COR-119.",
    )

    assert missing.error == "final_text_required"
    assert edited.result["decision"]["status"] == ApprovalStatus.EDITED
    assert "Redis fallback" in edited.result["decision"]["decision_text"]


async def test_non_canonical_actions_do_not_approve_memory() -> None:
    for action, expected in [
        ("proceed_with_warning", ApprovalStatus.NEEDS_REVIEW),
        ("stop", ApprovalStatus.NEEDS_REVIEW),
        ("reject", ApprovalStatus.REJECTED),
        ("mark_unresolved", ApprovalStatus.MARKED_UNRESOLVED),
    ]:
        service, decision_id = propose_decision()
        response = await service.approve_canonical_decision(
            decision_id=decision_id, action=action, actor_id="human_1"
        )
        assert response.result["decision"]["status"] == expected


async def test_supersede_marks_old_decision_inactive() -> None:
    service, old_id = propose_decision()
    approved = await service.approve_canonical_decision(
        decision_id=old_id, action="approve", actor_id="human_1"
    )
    evidence_pack_id = approved.result["decision"]["evidence_pack_id"]
    proposal = service.propose_canonical_decision(
        workspace_id="ws_1",
        evidence_pack_id=str(evidence_pack_id),
        scope_ref="COR-123",
        decision_text="Postgres is canonical; Redis fallback is removed.",
    )

    superseded = await service.approve_canonical_decision(
        decision_id=str(proposal.result["id"]),
        action="supersede",
        actor_id="human_1",
        supersedes_decision_id=old_id,
    )

    assert superseded.result["decision"]["status"] == ApprovalStatus.APPROVED
    assert superseded.result["decision"]["supersedes_decision_id"] == old_id
