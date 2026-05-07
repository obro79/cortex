from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cortex.contracts.entities import EvidencePack, RetrievalRequest

HIGH_RISK_TERMS = frozenset(
    {
        "migration",
        "billing",
        "infra",
        "infrastructure",
        "delete",
        "deletion",
        "data access",
        "permission",
        "secret",
        "token",
        "auth",
        "database",
        "schema",
    }
)


@dataclass(frozen=True)
class RiskClassification:
    category: str
    high_risk: bool


class RiskClassifier:
    def classify(
        self,
        *,
        query: str,
        evidence_pack: EvidencePack,
        retrieval_request: RetrievalRequest | None = None,
        task_hints: dict[str, object] | None = None,
    ) -> RiskClassification:
        hints = {
            **(retrieval_request.task_hints_json if retrieval_request else {}),
            **(task_hints or {}),
        }
        text = self._combined_text(query=query, hints=hints)
        conflict_summary = evidence_pack.conflict_summary_json
        permission_exclusions = evidence_pack.permission_exclusions_json
        missing_context = evidence_pack.missing_context_json
        stale_context = evidence_pack.stale_context_json

        if self._has_conflict(conflict_summary) or "cor-123" in text:
            return RiskClassification("architecture_conflict", True)
        if (
            self._has_permission_ambiguity(permission_exclusions)
            or "permission" in text
        ):
            return RiskClassification("permission_sensitive_ambiguity", True)
        if any(term in text for term in HIGH_RISK_TERMS):
            return RiskClassification(
                "migration_billing_infra_deletion_data_access", True
            )
        if self._count(missing_context, "missing_count", "omitted_count") > 0:
            return RiskClassification("missing_task_context", False)
        if self._count(stale_context, "stale_count") > 0:
            return RiskClassification("stale_context", False)
        if "maybe" in text or "unclear" in text or "ambiguous" in text:
            return RiskClassification("low_risk_ambiguity", False)
        return RiskClassification("clear_context", False)

    def _combined_text(self, *, query: str, hints: dict[str, object]) -> str:
        values: list[str] = [query]
        for value in hints.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(str(item) for item in value)
        return " ".join(values).lower()

    def _has_conflict(self, value: dict[str, Any]) -> bool:
        return self._count(value, "conflict_count") > 0 or bool(value.get("items"))

    def _has_permission_ambiguity(self, value: dict[str, Any]) -> bool:
        return bool(value) and self._count(value, "excluded_count") != 0

    def _count(self, value: dict[str, Any], *keys: str) -> int:
        for key in keys:
            count = value.get(key)
            if isinstance(count, int):
                return count
        return 0
