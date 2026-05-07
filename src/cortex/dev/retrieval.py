from __future__ import annotations

from typing import Any

from .evidence import EVIDENCE_PACK_ID, build_evidence_pack
from .fixtures import FixtureRepository


class DeterministicRetriever:
    def __init__(self, repository: FixtureRepository) -> None:
        self.repository = repository

    def query(self, query: str) -> dict[str, Any]:
        normalized_query = " ".join(query.lower().split())
        chunks = list(self.repository.source_chunks.values())
        lexical = [
            self._candidate(chunk.id, idx + 1, 1.0 - idx * 0.05, "lexical")
            for idx, chunk in enumerate(chunks)
        ]
        vector = [
            self._candidate(chunk.id, idx + 1, 0.95 - idx * 0.04, "vector")
            for idx, chunk in enumerate(chunks)
        ]
        relationship_expansions = [
            {
                "relationship_id": relationship["id"],
                "from_id": relationship["from_id"],
                "to_id": relationship["to_id"],
                "type": relationship["type"],
            }
            for relationship in self.repository.relationships
        ]
        final_ranking = [
            self._candidate(chunk.id, idx + 1, 1.0 - idx * 0.03, "merged")
            for idx, chunk in enumerate(chunks)
        ]
        evidence_pack = build_evidence_pack(self.repository)
        return {
            "query": query,
            "normalized_query": normalized_query,
            "filters": {"workspace_id": "ws_dev_cor_123", "fixture_bundle": "cor-123"},
            "lexical_candidates": lexical,
            "vector_candidates": vector,
            "relationship_expansions": relationship_expansions,
            "merged_candidates": final_ranking,
            "final_ranking": final_ranking,
            "excluded_candidates": [],
            "evidence_pack_id": EVIDENCE_PACK_ID,
            "gate_status": evidence_pack["gate_result"]["status"],
            "gate_result": evidence_pack["gate_result"],
            "expected_sources": [chunk.metadata_json["fixture_id"] for chunk in chunks],
        }

    def _candidate(
        self, chunk_id: str, rank: int, score: float, source: str
    ) -> dict[str, Any]:
        chunk = self.repository.source_chunks[chunk_id]
        return {
            "rank": rank,
            "score": round(score, 4),
            "source": source,
            "source_chunk_id": chunk.id,
            "source_object_id": chunk.source_object_id,
            "fixture_id": chunk.metadata_json["fixture_id"],
            "citation_label": chunk.citation_label,
            "is_stale": chunk.metadata_json["is_stale"],
        }
