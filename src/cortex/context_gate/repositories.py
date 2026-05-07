from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from cortex.contracts.entities import ContextGateResult
from cortex.contracts.enums import ContextGateStatus
from cortex.ingestion.payloads import sha256_digest

ALLOWED_COMPLETIONS = {
    "evaluating": {
        ContextGateStatus.ALLOW,
        ContextGateStatus.WARN,
        ContextGateStatus.BLOCK,
        ContextGateStatus.FAILED,
    }
}


class InvalidContextGateTransition(ValueError):
    pass


@dataclass(frozen=True)
class PendingContextGateResult:
    id: str
    workspace_id: str
    retrieval_request_id: str
    evidence_pack_id: str
    gate_version: str
    evaluated_at: datetime
    trace_id: str | None
    created_at: datetime
    updated_at: datetime
    status: str = "evaluating"


class InMemoryContextGateResultRepository:
    def __init__(self) -> None:
        self._records: dict[str, ContextGateResult] = {}
        self._pending: dict[str, PendingContextGateResult] = {}

    def create_evaluating(
        self,
        *,
        workspace_id: str,
        retrieval_request_id: str,
        evidence_pack_id: str,
        gate_version: str,
        trace_id: str | None = None,
    ) -> PendingContextGateResult:
        now = datetime.now(UTC)
        result_id = (
            "gate_"
            + sha256_digest(
                f"{workspace_id}:{retrieval_request_id}:{evidence_pack_id}:{now.isoformat()}".encode()
            ).removeprefix("sha256:")[:24]
        )
        record = PendingContextGateResult(
            id=result_id,
            workspace_id=workspace_id,
            retrieval_request_id=retrieval_request_id,
            evidence_pack_id=evidence_pack_id,
            gate_version=gate_version,
            evaluated_at=now,
            trace_id=trace_id,
            created_at=now,
            updated_at=now,
        )
        self._pending[record.id] = record
        return record

    def complete(
        self,
        result_id: str,
        *,
        status: ContextGateStatus,
        risk_category: str,
        reasons_json: dict[str, object],
        required_actions_json: dict[str, object],
    ) -> ContextGateResult:
        record = self._pending.pop(result_id)
        self._ensure_completion(record.status, status)
        now = datetime.now(UTC)
        completed = ContextGateResult(
            id=record.id,
            workspace_id=record.workspace_id,
            retrieval_request_id=record.retrieval_request_id,
            evidence_pack_id=record.evidence_pack_id,
            status=status,
            risk_category=risk_category,
            reasons_json=reasons_json,
            required_actions_json=required_actions_json,
            gate_version=record.gate_version,
            evaluated_at=now,
            trace_id=record.trace_id,
            created_at=record.created_at,
            updated_at=now,
        )
        self._records[result_id] = completed
        return completed

    def resolve(self, result_id: str, *, action: str) -> ContextGateResult:
        record = self._records[result_id]
        if record.status != ContextGateStatus.BLOCK:
            msg = f"invalid context gate resolution from status: {record.status}"
            raise InvalidContextGateTransition(msg)
        now = datetime.now(UTC)
        updated = record.model_copy(
            update={
                "resolved_at": now,
                "resolution_action": action,
                "updated_at": now,
            }
        )
        self._records[result_id] = updated
        return updated

    def get_by_id(self, result_id: str) -> ContextGateResult:
        return self._records[result_id]

    def _ensure_completion(self, current: str, desired: ContextGateStatus) -> None:
        if desired not in ALLOWED_COMPLETIONS.get(current, set()):
            msg = f"invalid context gate transition: {current} -> {desired}"
            raise InvalidContextGateTransition(msg)
