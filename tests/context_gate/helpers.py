from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import EvidencePack, RetrievalRequest
from cortex.contracts.enums import EvidencePackStatus


def make_request(query: str = "COR-123 session storage") -> RetrievalRequest:
    now = datetime.now(UTC)
    return RetrievalRequest(
        id="ret_1",
        workspace_id="ws_1",
        caller_type="mcp",
        query=query,
        task_hints_json={},
        filters_json={},
        status="completed",
        created_at=now,
        updated_at=now,
    )


def make_pack(
    *,
    conflict_count: int = 0,
    stale_count: int = 0,
    missing_count: int = 0,
    permission_exclusions: dict[str, object] | None = None,
    source_ids: list[str] | None = None,
    citations: list[dict[str, object]] | None = None,
) -> EvidencePack:
    now = datetime.now(UTC)
    return EvidencePack(
        id="ep_1",
        workspace_id="ws_1",
        retrieval_request_id="ret_1",
        status=EvidencePackStatus.CREATED,
        claims_json={},
        citations_json={
            "items": citations
            if citations is not None
            else [{"citation_id": "cite-1", "citation_label": "Allowed source"}]
        },
        candidate_summary_json={},
        source_coverage_json={"source_object_ids": source_ids or ["src_1", "src_2"]},
        permission_exclusions_json=permission_exclusions or {},
        missing_context_json={"missing_count": missing_count},
        stale_context_json={"stale_count": stale_count},
        conflict_summary_json={
            "conflict_count": conflict_count,
            "confidence": 0.9,
        },
        token_budget=4000,
        ranker_version="ranking-v1",
        created_at=now,
    )
