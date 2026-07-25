from __future__ import annotations

from cortex.canonical_memory.publishers import CanonicalDecisionPublisher
from cortex.canonical_memory.repositories import (
    InMemoryApprovalRecordRepository,
    InMemoryCanonicalDecisionRepository,
)
from cortex.canonical_memory.service import CanonicalDecisionService
from cortex.context_gate.repositories import InMemoryContextGateResultRepository
from cortex.contracts.entities import EvidencePack
from cortex.contracts.enums import EvidencePackStatus
from cortex.events.in_memory import InMemoryEventBus
from cortex.retrieval.repositories import InMemoryEvidencePackRepository


def make_service() -> tuple[
    CanonicalDecisionService,
    InMemoryCanonicalDecisionRepository,
    InMemoryApprovalRecordRepository,
    InMemoryEvidencePackRepository,
]:
    decisions = InMemoryCanonicalDecisionRepository()
    approvals = InMemoryApprovalRecordRepository()
    evidence = InMemoryEvidencePackRepository()
    gates = InMemoryContextGateResultRepository()
    service = CanonicalDecisionService(
        decisions=decisions,
        approvals=approvals,
        evidence=evidence,
        gates=gates,
        publisher=CanonicalDecisionPublisher(InMemoryEventBus()),
    )
    return service, decisions, approvals, evidence


def seed_evidence(repository: InMemoryEvidencePackRepository) -> str:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    pack = EvidencePack(
        id="ep_1",
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        status=EvidencePackStatus.CREATED,
        claims_json={"items": [{"claim": "Session storage guidance"}]},
        citations_json={"items": [{"citation_id": "cite-1"}]},
        candidate_summary_json={},
        source_coverage_json={"source_object_ids": ["src_1"]},
        permission_exclusions_json={},
        missing_context_json={},
        stale_context_json={"stale_count": 0},
        conflict_summary_json={"conflict_count": 0},
        token_budget=4000,
        ranker_version="ranking-v1",
        created_at=now,
    )
    repository._records[pack.id] = pack
    return pack.id
