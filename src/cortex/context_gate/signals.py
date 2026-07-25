from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cortex.contracts.entities import EvidencePack


@dataclass(frozen=True)
class GateSignal:
    kind: str
    message: str
    citation_ids: tuple[str, ...] = ()
    confidence: float = 1.0


class EvidenceSignalExtractor:
    def extract(self, evidence_pack: EvidencePack) -> list[GateSignal]:
        citation_ids = self._citation_ids(evidence_pack)
        signals: list[GateSignal] = []
        conflict_count = self._count(
            evidence_pack.conflict_summary_json, "conflict_count"
        )
        if conflict_count or evidence_pack.conflict_summary_json.get("items"):
            signals.append(
                GateSignal(
                    kind="conflict",
                    message="Retrieved evidence contains conflicting context.",
                    citation_ids=citation_ids[:2],
                    confidence=float(
                        evidence_pack.conflict_summary_json.get("confidence", 0.9)
                    ),
                )
            )
        if self._count(evidence_pack.stale_context_json, "stale_count") > 0:
            signals.append(
                GateSignal(
                    kind="stale_context",
                    message="Some cited evidence is stale.",
                    citation_ids=citation_ids[:2],
                    confidence=0.8,
                )
            )
        if (
            self._count(
                evidence_pack.missing_context_json, "missing_count", "omitted_count"
            )
            > 0
        ):
            signals.append(
                GateSignal(
                    kind="missing_context",
                    message="Relevant task context may be missing.",
                    citation_ids=citation_ids[:1],
                    confidence=0.7,
                )
            )
        if self._has_permission_exclusions(evidence_pack.permission_exclusions_json):
            signals.append(
                GateSignal(
                    kind="permission_ambiguity",
                    message="Permission exclusions affect retrieved context.",
                    citation_ids=citation_ids[:1],
                    confidence=1.0,
                )
            )
        source_count = len(self._source_ids(evidence_pack.source_coverage_json))
        signals.append(
            GateSignal(
                kind="source_coverage",
                message=f"{source_count} allowlisted source(s) represented.",
                citation_ids=citation_ids[:1],
                confidence=1.0,
            )
        )
        if not [signal for signal in signals if signal.kind != "source_coverage"]:
            signals.append(
                GateSignal(
                    kind="clear_context",
                    message="Current cited evidence is sufficient.",
                    citation_ids=citation_ids[:2],
                    confidence=1.0,
                )
            )
        return signals

    def _citation_ids(self, evidence_pack: EvidencePack) -> tuple[str, ...]:
        citations = evidence_pack.citations_json.get("items", [])
        if not isinstance(citations, list):
            return ()
        ids: list[str] = []
        for index, citation in enumerate(citations, start=1):
            if not isinstance(citation, dict):
                continue
            citation_id = citation.get("citation_id")
            if isinstance(citation_id, str) and citation_id:
                ids.append(citation_id)
            else:
                ids.append(f"cite-{index}")
        return tuple(ids)

    def _source_ids(self, coverage: dict[str, Any]) -> set[str]:
        values = coverage.get("source_object_ids")
        if isinstance(values, list):
            return {str(value) for value in values}
        return {key for key, value in coverage.items() if value is True}

    def _count(self, value: dict[str, Any], *keys: str) -> int:
        for key in keys:
            count = value.get(key)
            if isinstance(count, int):
                return count
        return 0

    def _has_permission_exclusions(self, value: dict[str, Any]) -> bool:
        if not value:
            return False
        count = value.get("excluded_count")
        return count != 0
