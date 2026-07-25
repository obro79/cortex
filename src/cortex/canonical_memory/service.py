from __future__ import annotations

from dataclasses import dataclass

from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.contracts.entities import CanonicalDecision, EvidencePack
from cortex.contracts.enums import ApprovalStatus
from cortex.retrieval.repositories import InMemoryEvidencePackRepository

from .publishers import CanonicalDecisionPublisher
from .render import CanonicalDecisionRenderer
from .repositories import (
    CanonicalMemoryError,
    InMemoryApprovalRecordRepository,
    InMemoryCanonicalDecisionRepository,
)

APPROVAL_ACTIONS = {
    "approve",
    "edit",
    "proceed_with_warning",
    "mark_unresolved",
    "reject",
    "stop",
    "supersede",
}


@dataclass(frozen=True)
class CanonicalMemoryResponse:
    ok: bool
    text: str
    result: dict[str, object]
    error: str | None = None


class CanonicalDecisionService:
    def __init__(
        self,
        *,
        decisions: InMemoryCanonicalDecisionRepository,
        approvals: InMemoryApprovalRecordRepository,
        evidence: InMemoryEvidencePackRepository,
        gates: InMemoryContextGateResultRepository,
        publisher: CanonicalDecisionPublisher,
    ) -> None:
        self.decisions = decisions
        self.approvals = approvals
        self.evidence = evidence
        self.gates = gates
        self.publisher = publisher
        self.renderer = CanonicalDecisionRenderer()

    def propose_canonical_decision(
        self,
        *,
        workspace_id: str,
        evidence_pack_id: str | None = None,
        context_gate_result_id: str | None = None,
        scope_type: str | None = None,
        scope_ref: str | None = None,
        title: str | None = None,
        decision_text: str | None = None,
        actor_id: str | None = None,
    ) -> CanonicalMemoryResponse:
        try:
            pack = self._resolve_evidence_pack(
                evidence_pack_id=evidence_pack_id,
                context_gate_result_id=context_gate_result_id,
            )
            citation_ids = self._citation_ids(pack)
            if not citation_ids:
                return self._error("missing_citations")
            resolved_scope_type = scope_type or "task"
            resolved_scope_ref = scope_ref or self._derive_scope_ref(pack)
            default_text = (
                "Resolve the cited context as the canonical implementation guidance."
            )
            decision = self.decisions.create_needs_review(
                workspace_id=workspace_id,
                scope_type=resolved_scope_type,
                scope_ref=resolved_scope_ref,
                title=title or self._derive_title(resolved_scope_ref),
                decision_text=decision_text or default_text,
                evidence_pack_id=pack.id,
                source_citations_json={"citation_ids": citation_ids},
                stale_or_superseded_evidence_json={
                    "stale_context": pack.stale_context_json,
                    "conflict_summary": pack.conflict_summary_json,
                },
                created_by_actor_id=actor_id,
            )
        except KeyError:
            return self._error("not_found")
        return CanonicalMemoryResponse(
            ok=True,
            text=self.renderer.render_proposal(decision),
            result=decision.model_dump(mode="json"),
        )

    async def approve_canonical_decision(
        self,
        *,
        decision_id: str,
        action: str,
        actor_id: str | None,
        final_text: str | None = None,
        rationale: str | None = None,
        supersedes_decision_id: str | None = None,
    ) -> CanonicalMemoryResponse:
        if action not in APPROVAL_ACTIONS:
            return self._error("invalid_action")
        if not actor_id or actor_id.startswith("agent_"):
            return self._error("human_actor_required")
        try:
            decision = self.decisions.get_by_id(decision_id)
            original_text = decision.decision_text
            if action == "edit" and not final_text:
                return self._error("final_text_required")
            approval = self.approvals.create(
                workspace_id=decision.workspace_id,
                actor_id=actor_id,
                target_type="canonical_decision",
                target_id=decision.id,
                action=action,
                original_text=original_text,
                final_text=final_text or original_text,
                rationale=rationale,
                evidence_pack_id=decision.evidence_pack_id,
            )
            updated = await self._apply_action(
                decision=decision,
                action=action,
                actor_id=actor_id,
                final_text=final_text,
                supersedes_decision_id=supersedes_decision_id,
            )
        except KeyError:
            return self._error("unknown_decision_id")
        except CanonicalMemoryError as error:
            return self._error(str(error))

        return CanonicalMemoryResponse(
            ok=True,
            text=self.renderer.render_approval(updated, action),
            result={
                "decision": updated.model_dump(mode="json"),
                "approval_record": approval.model_dump(mode="json"),
            },
        )

    async def _apply_action(
        self,
        *,
        decision: CanonicalDecision,
        action: str,
        actor_id: str,
        final_text: str | None,
        supersedes_decision_id: str | None,
    ) -> CanonicalDecision:
        if action == "approve":
            updated = self.decisions.update_after_action(
                decision.id, status=ApprovalStatus.APPROVED, actor_id=actor_id
            )
            await self.publisher.publish_approved(updated, action=action)
            return updated
        if action == "edit":
            updated = self.decisions.update_after_action(
                decision.id,
                status=ApprovalStatus.EDITED,
                actor_id=actor_id,
                decision_text=final_text,
            )
            await self.publisher.publish_approved(updated, action=action)
            return updated
        if action == "reject":
            return self.decisions.update_after_action(
                decision.id, status=ApprovalStatus.REJECTED
            )
        if action == "mark_unresolved":
            return self.decisions.update_after_action(
                decision.id, status=ApprovalStatus.MARKED_UNRESOLVED
            )
        if action == "supersede":
            if not supersedes_decision_id:
                raise CanonicalMemoryError("supersedes_decision_id_required")
            _old, replacement = self.decisions.supersede(
                old_decision_id=supersedes_decision_id,
                replacement_decision_id=decision.id,
                actor_id=actor_id,
            )
            await self.publisher.publish_approved(replacement, action=action)
            return replacement
        return decision

    def _resolve_evidence_pack(
        self,
        *,
        evidence_pack_id: str | None,
        context_gate_result_id: str | None,
    ) -> EvidencePack:
        if evidence_pack_id:
            return self.evidence.get_by_id(evidence_pack_id)
        if context_gate_result_id:
            gate = self.gates.get_by_id(context_gate_result_id)
            return self.evidence.get_by_id(gate.evidence_pack_id)
        raise KeyError("evidence_pack")

    def _citation_ids(self, pack: EvidencePack) -> list[str]:
        citations = pack.citations_json.get("items", [])
        if not isinstance(citations, list):
            return []
        ids: list[str] = []
        for index, citation in enumerate(citations, start=1):
            if not isinstance(citation, dict):
                continue
            citation_id = citation.get("citation_id")
            ids.append(str(citation_id or f"cite-{index}"))
        return ids

    def _derive_scope_ref(self, pack: EvidencePack) -> str:
        claims = pack.claims_json.get("items", [])
        if isinstance(claims, list) and claims:
            first = claims[0]
            if isinstance(first, dict):
                claim = first.get("claim")
                if isinstance(claim, str) and claim:
                    return claim[:80]
        return pack.retrieval_request_id

    def _derive_title(self, scope_ref: str) -> str:
        if "session" in scope_ref.lower():
            return "Session storage canonical decision"
        return "Canonical decision"

    def _error(self, code: str) -> CanonicalMemoryResponse:
        return CanonicalMemoryResponse(ok=False, text="", result={}, error=code)
