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
            },
            "source_coverage_json": {
                "source_object_ids": sorted(
                    {candidate.source_chunk.source_object_id for candidate in selected}
                )
            },
            "permission_exclusions_json": dict(permission_exclusions),
            "missing_context_json": {
                "omitted_count": max(0, len(candidates) - len(selected))
            },
            "stale_context_json": {
                "stale_count": sum(
                    1
                    for candidate in selected
                    if candidate.source_chunk.metadata_json.get("is_stale") is True
                )
            },
            "conflict_summary_json": {"conflict_count": 0},
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
