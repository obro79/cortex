from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cortex.contracts.entities import EvidencePack, RetrievalRequest
from cortex.contracts.enums import EvidencePackStatus
from cortex.ingestion.payloads import sha256_digest


class InMemoryRetrievalRequestRepository:
    def __init__(self) -> None:
        self._records: dict[str, RetrievalRequest] = {}

    def create(
        self,
        *,
        workspace_id: str,
        query: str,
        caller_type: str = "mcp",
        caller_id: str | None = None,
        task_hints_json: dict[str, object] | None = None,
        filters_json: dict[str, object] | None = None,
        source_allowlist_snapshot_hash: str | None = None,
    ) -> RetrievalRequest:
        now = datetime.now(UTC)
        record = RetrievalRequest(
            id=f"ret_{sha256_digest(f'{workspace_id}:{query}:{now.isoformat()}'.encode()).removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            caller_type=caller_type,
            caller_id=caller_id,
            query=query,
            task_hints_json=task_hints_json or {},
            filters_json=filters_json or {},
            source_allowlist_snapshot_hash=source_allowlist_snapshot_hash,
            status="received",
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        return record

    def mark_completed(
        self, request_id: str, *, status: str = "completed"
    ) -> RetrievalRequest:
        record = self._records[request_id]
        now = datetime.now(UTC)
        updated = record.model_copy(
            update={
                "status": status,
                "completed_at": now,
                "latency_ms": int(
                    (now - (record.started_at or now)).total_seconds() * 1000
                ),
                "updated_at": now,
            }
        )
        self._records[request_id] = updated
        return updated


class InMemoryEvidencePackRepository:
    def __init__(self) -> None:
        self._records: dict[str, EvidencePack] = {}

    def create(
        self,
        *,
        workspace_id: str,
        retrieval_request_id: str,
        claims_json: dict[str, object],
        citations_json: dict[str, object],
        candidate_summary_json: dict[str, object],
        source_coverage_json: dict[str, object],
        permission_exclusions_json: dict[str, object],
        missing_context_json: dict[str, object],
        stale_context_json: dict[str, object],
        conflict_summary_json: dict[str, object],
        token_budget: int,
        ranker_version: str,
    ) -> EvidencePack:
        now = datetime.now(UTC)
        record = EvidencePack(
            id=f"ep_{sha256_digest(f'{workspace_id}:{retrieval_request_id}'.encode()).removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            retrieval_request_id=retrieval_request_id,
            status=EvidencePackStatus.CREATED,
            claims_json=claims_json,
            citations_json=citations_json,
            candidate_summary_json=candidate_summary_json,
            source_coverage_json=source_coverage_json,
            permission_exclusions_json=permission_exclusions_json,
            missing_context_json=missing_context_json,
            stale_context_json=stale_context_json,
            conflict_summary_json=conflict_summary_json,
            token_budget=token_budget,
            ranker_version=ranker_version,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        self._records[record.id] = record
        return record

    def get_by_id(self, evidence_pack_id: str) -> EvidencePack:
        return self._records[evidence_pack_id]
