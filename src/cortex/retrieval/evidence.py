from __future__ import annotations

from collections.abc import Mapping

from cortex.contracts.entities import EvidencePack

from .candidates import Candidate


class EvidencePackBuilder:
    def build_payloads(
        self,
        *,
        candidates: list[Candidate],
        permission_exclusions: Mapping[str, object],
        token_budget: int,
        versions: dict[str, str],
    ) -> dict[str, dict[str, object]]:
        selected = candidates[: int(versions.get("final_evidence_limit", "12"))]
        citations = [
            {
                "source_chunk_id": candidate.source_chunk.id,
                "source_object_id": candidate.source_chunk.source_object_id,
                "citation_label": candidate.source_chunk.citation_label,
                "citation_url": candidate.source_chunk.citation_url,
                "snippet": self._snippet(candidate.source_chunk.text, token_budget),
            }
            for candidate in selected
        ]
        provider_set: set[str] = set()
        for candidate in selected:
            provider = self._provider_from_chunk(candidate.source_chunk)
            if provider:
                provider_set.add(provider)
        providers = sorted(provider_set)
        stale_count = sum(
            1
            for candidate in selected
            if candidate.source_chunk.metadata_json.get("is_stale") is True
        )
        conflict_count = 1 if stale_count and len(providers) > 1 else 0
        return {
            "claims_json": {
                "items": [
                    {
                        "claim": "Relevant context retrieved",
                        "citation_count": len(citations),
                    }
                ]
            },
            "citations_json": {"items": citations},
            "candidate_summary_json": {
                "candidate_count": len(candidates),
                "versions": versions,
                "selected_candidates": [
                    {
                        "source_chunk_id": candidate.source_chunk.id,
                        "sources": sorted(candidate.paths),
                        "scores": dict(sorted(candidate.score_provenance.items())),
                    }
                    for candidate in selected
                ],
            },
            "source_coverage_json": {
                "providers": providers,
                "source_object_ids": sorted(
                    {candidate.source_chunk.source_object_id for candidate in selected}
                ),
            },
            "permission_exclusions_json": dict(permission_exclusions),
            "missing_context_json": {
                "omitted_count": max(0, len(candidates) - len(selected))
            },
            "stale_context_json": {
                "stale_count": stale_count,
            },
            "conflict_summary_json": {
                "conflict_count": conflict_count,
                "confidence": 0.9 if conflict_count else 0,
            },
        }

    def render_text(self, evidence_pack: EvidencePack) -> str:
        citations = evidence_pack.citations_json.get("items", [])
        if not isinstance(citations, list):
            return "No cited context found."
        lines = []
        for index, citation in enumerate(citations, start=1):
            if isinstance(citation, dict):
                label = citation.get("citation_label")
                snippet = citation.get("snippet")
                lines.append(f"[{index}] {label}: {snippet}")
        return "\n".join(lines) or "No cited context found."

    def _snippet(self, text: str, token_budget: int) -> str:
        words = text.split()
        return " ".join(words[: min(len(words), token_budget)])

    def _provider_from_chunk(self, chunk: object) -> str | None:
        metadata = getattr(chunk, "metadata_json", {})
        if not isinstance(metadata, dict):
            return None
        object_type = metadata.get("object_type")
        if object_type == "slack_thread":
            return "slack"
        if object_type == "linear_issue":
            return "linear"
        if object_type in {"github_pull_request", "github_issue", "github_commit"}:
            return "github"
        if object_type == "repo_doc":
            return "repo_docs"
        return None
