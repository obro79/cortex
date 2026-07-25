from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import ApprovalRecord, CanonicalDecision
from cortex.contracts.enums import ApprovalStatus
from cortex.ingestion.payloads import sha256_digest

ACTIVE_STATUSES = {ApprovalStatus.APPROVED, ApprovalStatus.EDITED}


class CanonicalMemoryError(ValueError):
    pass


class InMemoryCanonicalDecisionRepository:
    def __init__(self) -> None:
        self._records: dict[str, CanonicalDecision] = {}

    def create_needs_review(
        self,
        *,
        workspace_id: str,
        scope_type: str,
        scope_ref: str,
        title: str,
        decision_text: str,
        evidence_pack_id: str,
        source_citations_json: dict[str, object],
        stale_or_superseded_evidence_json: dict[str, object] | None = None,
        created_by_actor_id: str | None = None,
        supersedes_decision_id: str | None = None,
    ) -> CanonicalDecision:
        now = datetime.now(UTC)
        decision_id = (
            "cd_"
            + sha256_digest(
                f"{workspace_id}:{scope_type}:{scope_ref}:{now.isoformat()}".encode()
            ).removeprefix("sha256:")[:24]
        )
        if supersedes_decision_id:
            self._reject_supersession_cycle(decision_id, supersedes_decision_id)
        record = CanonicalDecision(
            id=decision_id,
            workspace_id=workspace_id,
            scope_type=scope_type,
            scope_ref=scope_ref,
            title=title,
            decision_text=decision_text,
            status=ApprovalStatus.NEEDS_REVIEW,
            evidence_pack_id=evidence_pack_id,
            supersedes_decision_id=supersedes_decision_id,
            created_by_actor_id=created_by_actor_id,
            source_citations_json=source_citations_json,
            stale_or_superseded_evidence_json=stale_or_superseded_evidence_json or {},
            decision_version="canonical-decision-v1",
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        return record

    def get_by_id(self, decision_id: str) -> CanonicalDecision:
        return self._records[decision_id]

    def list_active(self, workspace_id: str) -> list[CanonicalDecision]:
        return [
            record
            for record in self._records.values()
            if record.workspace_id == workspace_id
            and ApprovalStatus(record.status) in ACTIVE_STATUSES
            and record.superseded_by_decision_id is None
        ]

    def update_after_action(
        self,
        decision_id: str,
        *,
        status: ApprovalStatus,
        actor_id: str | None = None,
        decision_text: str | None = None,
    ) -> CanonicalDecision:
        record = self._records[decision_id]
        self._ensure_transition(ApprovalStatus(record.status), status)
        now = datetime.now(UTC)
        update: dict[str, object] = {"status": status, "updated_at": now}
        if decision_text is not None:
            update["decision_text"] = decision_text
        if status in ACTIVE_STATUSES:
            update["approved_by_actor_id"] = actor_id
            update["approved_at"] = now
        updated = record.model_copy(update=update)
        self._records[decision_id] = updated
        return updated

    def supersede(
        self,
        *,
        old_decision_id: str,
        replacement_decision_id: str,
        actor_id: str,
    ) -> tuple[CanonicalDecision, CanonicalDecision]:
        old = self._records[old_decision_id]
        replacement = self._records[replacement_decision_id]
        if ApprovalStatus(old.status) not in ACTIVE_STATUSES:
            raise CanonicalMemoryError(
                "only approved or edited decisions can supersede"
            )
        self._reject_supersession_cycle(replacement_decision_id, old_decision_id)
        now = datetime.now(UTC)
        updated_old = old.model_copy(
            update={
                "status": ApprovalStatus.SUPERSEDED,
                "superseded_by_decision_id": replacement.id,
                "updated_at": now,
            }
        )
        updated_replacement = replacement.model_copy(
            update={
                "status": ApprovalStatus.APPROVED,
                "supersedes_decision_id": old.id,
                "approved_by_actor_id": actor_id,
                "approved_at": now,
                "updated_at": now,
            }
        )
        self._records[old.id] = updated_old
        self._records[replacement.id] = updated_replacement
        return updated_old, updated_replacement

    def _ensure_transition(
        self, current: ApprovalStatus, desired: ApprovalStatus
    ) -> None:
        if current != ApprovalStatus.NEEDS_REVIEW:
            raise CanonicalMemoryError(f"decision is not pending review: {current}")
        if desired not in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.EDITED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.MARKED_UNRESOLVED,
        }:
            raise CanonicalMemoryError(f"invalid canonical decision status: {desired}")

    def _reject_supersession_cycle(
        self, decision_id: str, supersedes_decision_id: str
    ) -> None:
        current: str | None = supersedes_decision_id
        seen = {decision_id}
        while current:
            if current in seen:
                raise CanonicalMemoryError("canonical supersession cycle detected")
            seen.add(current)
            parent = self._records.get(current)
            current = parent.supersedes_decision_id if parent else None


class InMemoryApprovalRecordRepository:
    def __init__(self) -> None:
        self._records: dict[str, ApprovalRecord] = {}

    def create(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        target_type: str,
        target_id: str,
        action: str,
        original_text: str | None = None,
        final_text: str | None = None,
        rationale: str | None = None,
        evidence_pack_id: str | None = None,
        trace_id: str | None = None,
    ) -> ApprovalRecord:
        now = datetime.now(UTC)
        record_id = (
            "apr_"
            + sha256_digest(
                f"{workspace_id}:{actor_id}:{target_id}:{action}:{now.isoformat()}".encode()
            ).removeprefix("sha256:")[:24]
        )
        record = ApprovalRecord(
            id=record_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            original_text=original_text,
            final_text=final_text,
            rationale=rationale,
            evidence_pack_id=evidence_pack_id,
            created_at=now,
            trace_id=trace_id,
        )
        self._records[record.id] = record
        return record

    def list_for_target(self, target_type: str, target_id: str) -> list[ApprovalRecord]:
        return [
            record
            for record in self._records.values()
            if record.target_type == target_type and record.target_id == target_id
        ]
