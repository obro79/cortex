from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import CanonicalDecision, SourceChunk
from cortex.contracts.enums import SourceChunkStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.retrieval.candidates import Candidate


class CanonicalDecisionCandidateAdapter:
    def candidates_for_query(
        self, *, decisions: list[CanonicalDecision], query: str
    ) -> list[Candidate]:
        terms = query.lower().split()
        candidates: list[Candidate] = []
        for decision in decisions:
            haystack = f"{decision.title} {decision.decision_text}".lower()
            if terms and not any(term in haystack for term in terms):
                continue
            candidates.append(
                Candidate(
                    source_chunk=self._to_chunk(decision),
                    lexical_score=1.0,
                    source_authority_score=10.0,
                    paths={"canonical_decision"},
                )
            )
        return candidates

    def _to_chunk(self, decision: CanonicalDecision) -> SourceChunk:
        now = datetime.now(UTC)
        text_hash = sha256_digest(decision.decision_text.encode())
        return SourceChunk(
            id=f"chunk_{decision.id}",
            workspace_id=decision.workspace_id,
            source_object_id=decision.id,
            chunk_type="canonical_decision",
            chunk_index=0,
            text=decision.decision_text,
            text_hash=text_hash,
            token_count=len(decision.decision_text.split()),
            chunking_version="canonical-decision-v1",
            citation_label=decision.title,
            citation_url=None,
            metadata_json={
                "source_kind": "canonical_decision",
                "decision_id": decision.id,
                "status": decision.status,
                "approved_by_actor_id": decision.approved_by_actor_id,
                "approved_at": (
                    decision.approved_at.isoformat() if decision.approved_at else None
                ),
            },
            status=SourceChunkStatus.ACTIVE,
            created_from_hash=text_hash,
            created_at=decision.approved_at or now,
            updated_at=decision.updated_at,
        )
