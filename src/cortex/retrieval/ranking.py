from __future__ import annotations

from collections import defaultdict

from .candidates import Candidate


class CandidateRanker:
    def __init__(self, weights: dict[str, float | str]) -> None:
        self.weights = weights
        base_sum = sum(
            float(weights[key])
            for key in [
                "vector_weight",
                "lexical_weight",
                "recency_weight",
                "relationship_weight",
                "source_authority_weight",
            ]
        )
        if round(base_sum, 6) != 1.0:
            raise ValueError("base ranking weights must sum to 1.0")

    def rank(
        self, candidates: list[Candidate], max_per_source_object: int
    ) -> list[Candidate]:
        merged: dict[str, Candidate] = {}
        for candidate in candidates:
            existing = merged.get(candidate.id)
            if existing is None:
                merged[candidate.id] = candidate
                continue
            merged[candidate.id] = Candidate(
                source_chunk=candidate.source_chunk,
                lexical_score=max(existing.lexical_score, candidate.lexical_score),
                vector_score=max(existing.vector_score, candidate.vector_score),
                relationship_score=max(
                    existing.relationship_score, candidate.relationship_score
                ),
                source_authority_score=max(
                    existing.source_authority_score,
                    candidate.source_authority_score,
                ),
                paths=existing.paths | candidate.paths,
                score_provenance={
                    **existing.score_provenance,
                    **{
                        name: max(float(existing.score_provenance.get(name, 0)), value)
                        for name, value in candidate.score_provenance.items()
                    },
                },
            )
        per_source: dict[str, int] = defaultdict(int)
        ranked = []
        for candidate in sorted(
            merged.values(),
            key=lambda candidate: (-self.score(candidate), candidate.id),
        ):
            source_id = candidate.source_chunk.source_object_id
            if per_source[source_id] >= max_per_source_object:
                continue
            ranked.append(candidate)
            per_source[source_id] += 1
        return ranked

    def score(self, candidate: Candidate) -> float:
        return (
            candidate.vector_score * float(self.weights["vector_weight"])
            + candidate.lexical_score * float(self.weights["lexical_weight"])
            + candidate.relationship_score * float(self.weights["relationship_weight"])
            + candidate.source_authority_score
            * float(self.weights["source_authority_weight"])
        )
