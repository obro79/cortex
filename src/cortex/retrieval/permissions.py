from __future__ import annotations

from cortex.permissions.provider_acls import ProviderAclPrincipal
from cortex.permissions.service import PermissionService

from .candidates import Candidate
from .query import QueryPlan


class PermissionFilter:
    def __init__(
        self,
        *,
        workspace_id: str | None = None,
        service: PermissionService | None = None,
        caller_principals: list[ProviderAclPrincipal] | None = None,
    ) -> None:
        self.workspace_id = workspace_id
        self.service = service
        self.caller_principals = caller_principals

    def filter(
        self, candidates: list[Candidate], plan: QueryPlan
    ) -> tuple[list[Candidate], dict[str, int | str]]:
        if self.service is not None:
            if self.workspace_id is None:
                return [], {
                    "excluded_count": len(candidates),
                    "reason": "missing_workspace",
                }
            result = self.service.filter_candidates(
                workspace_id=self.workspace_id,
                candidates=candidates,
                source_object_allowlist=plan.source_allowlist,
                caller_principals=self.caller_principals,
            )
            return result.candidates, result.exclusions
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
