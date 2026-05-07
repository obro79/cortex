from __future__ import annotations

from .candidates import Candidate
from .query import QueryPlan


class PermissionFilter:
    def filter(
        self, candidates: list[Candidate], plan: QueryPlan
    ) -> tuple[list[Candidate], dict[str, int | str]]:
        if not plan.source_allowlist:
            return candidates, {"excluded_count": 0}
        allowlist = set(plan.source_allowlist)
        allowed = [
            candidate
            for candidate in candidates
            if candidate.source_chunk.source_object_id in allowlist
        ]
        return allowed, {
            "excluded_count": len(candidates) - len(allowed),
            "reason": "source_allowlist",
        }
