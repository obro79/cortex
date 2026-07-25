from __future__ import annotations

from collections.abc import Iterable

from cortex.contracts.enums import SourceChunkStatus

from .candidates import Candidate
from .ranking import CandidateRanker


class HybridCandidateFuser:
    """Fuse independently retrieved lexical and vector candidates in-memory.

    Retrieval adapters remain responsible for obtaining candidates. This boundary
    only applies query-time eligibility and combines their scores/provenance, so
    it works with both in-memory fixtures and future storage-backed adapters.
    """

    def fuse(
        self,
        *,
        workspace_id: str,
        lexical_candidates: Iterable[Candidate],
        vector_candidates: Iterable[Candidate],
        provider_filters: Iterable[str] = (),
        additional_candidates: Iterable[Candidate] = (),
        limit: int | None = None,
        ranker: CandidateRanker | None = None,
        max_per_source_object: int | None = None,
    ) -> list[Candidate]:
        allowed_providers = {
            provider.strip().lower()
            for provider in provider_filters
            if isinstance(provider, str) and provider.strip()
        }
        merged: dict[str, Candidate] = {}
        candidate_sets = (
            ("fts", lexical_candidates),
            ("vector", vector_candidates),
            ("additional", additional_candidates),
        )
        for channel, candidates in candidate_sets:
            for candidate in candidates:
                if not self._is_eligible(candidate, workspace_id, allowed_providers):
                    continue
                annotated = self._annotate(candidate, channel)
                existing = merged.get(annotated.id)
                merged[annotated.id] = (
                    annotated if existing is None else self._merge(existing, annotated)
                )
        fused = list(merged.values())
        if limit is not None and ranker is not None:
            if max_per_source_object is None:
                raise ValueError(
                    "max_per_source_object is required when limiting with a ranker"
                )
            return ranker.rank(
                fused, max_per_source_object=max_per_source_object
            )[:limit]
        fused.sort(
            key=lambda candidate: (
                -max(
                    candidate.lexical_score,
                    candidate.vector_score,
                    candidate.relationship_score,
                    candidate.source_authority_score,
                ),
                candidate.id,
            )
        )
        return fused[:limit] if limit is not None else fused

    def _is_eligible(
        self,
        candidate: Candidate,
        workspace_id: str,
        allowed_providers: set[str],
    ) -> bool:
        chunk = candidate.source_chunk
        if (
            chunk.workspace_id != workspace_id
            or chunk.status != SourceChunkStatus.ACTIVE
        ):
            return False
        return not allowed_providers or self.provider(candidate) in allowed_providers

    def _annotate(self, candidate: Candidate, channel: str) -> Candidate:
        provenance = self._score_provenance(candidate)
        if channel == "fts" and candidate.lexical_score:
            provenance["lexical"] = max(
                provenance.get("lexical", 0.0), candidate.lexical_score
            )
        if channel == "vector" and candidate.vector_score:
            provenance["vector"] = max(
                provenance.get("vector", 0.0), candidate.vector_score
            )
        return Candidate(
            source_chunk=candidate.source_chunk,
            lexical_score=candidate.lexical_score,
            vector_score=candidate.vector_score,
            relationship_score=candidate.relationship_score,
            source_authority_score=candidate.source_authority_score,
            paths=candidate.paths | {channel},
            score_provenance=provenance,
        )

    def _merge(self, first: Candidate, second: Candidate) -> Candidate:
        provenance = self._score_provenance(first)
        for name, value in self._score_provenance(second).items():
            provenance[name] = max(provenance.get(name, 0.0), value)
        return Candidate(
            source_chunk=first.source_chunk,
            lexical_score=max(first.lexical_score, second.lexical_score),
            vector_score=max(first.vector_score, second.vector_score),
            relationship_score=max(first.relationship_score, second.relationship_score),
            source_authority_score=max(
                first.source_authority_score, second.source_authority_score
            ),
            paths=first.paths | second.paths,
            score_provenance=provenance,
        )

    def _score_provenance(self, candidate: Candidate) -> dict[str, float]:
        provenance = dict(candidate.score_provenance)
        for name, value in (
            ("lexical", candidate.lexical_score),
            ("vector", candidate.vector_score),
            ("relationship", candidate.relationship_score),
            ("source_authority", candidate.source_authority_score),
        ):
            if value:
                provenance[name] = max(provenance.get(name, 0.0), value)
        return provenance

    @staticmethod
    def provider(candidate: Candidate) -> str | None:
        metadata = candidate.source_chunk.metadata_json
        if not isinstance(metadata, dict):
            return None
        provider = metadata.get("provider")
        if isinstance(provider, str):
            return provider.lower()
        object_type = metadata.get("object_type")
        provider_by_object_type = {
            "slack_thread": "slack",
            "linear_issue": "linear",
            "github_pull_request": "github",
            "github_issue": "github",
            "github_commit": "github",
            "repo_doc": "repo_docs",
        }
        if not isinstance(object_type, str):
            return None
        return provider_by_object_type.get(object_type)
