from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cortex.contracts.entities import PermissionScope, SourceChunk
from cortex.retrieval.candidates import Candidate

from .scopes import InMemoryPermissionScopeRepository, scope_external_id_hash

PermissionDecision = Literal["allowed", "denied"]


@dataclass(frozen=True)
class PermissionCheck:
    decision: PermissionDecision
    reason: str


@dataclass(frozen=True)
class PermissionFilterResult:
    candidates: list[Candidate]
    exclusions: dict[str, int | str]


class PermissionService:
    def __init__(self, scopes: InMemoryPermissionScopeRepository) -> None:
        self.scopes = scopes

    def snapshot_hash(self, workspace_id: str) -> str:
        return self.scopes.create_snapshot(workspace_id).snapshot_hash

    def check_chunk(
        self,
        *,
        workspace_id: str,
        chunk: SourceChunk,
        source_object_allowlist: list[str] | None = None,
    ) -> PermissionCheck:
        if chunk.workspace_id != workspace_id:
            return PermissionCheck(decision="denied", reason="workspace_mismatch")
        if (
            source_object_allowlist
            and chunk.source_object_id in source_object_allowlist
        ):
            return PermissionCheck(decision="allowed", reason="source_object_allowlist")

        active = self.scopes.list_active(workspace_id)
        if not active:
            return PermissionCheck(
                decision="denied", reason="no_active_permission_scope"
            )
        if self._matches_any_scope(chunk, active):
            return PermissionCheck(decision="allowed", reason="permission_scope")
        return PermissionCheck(decision="denied", reason="permission_scope")

    def filter_candidates(
        self,
        *,
        workspace_id: str,
        candidates: list[Candidate],
        source_object_allowlist: list[str] | None = None,
    ) -> PermissionFilterResult:
        allowed: list[Candidate] = []
        denied_count = 0
        reason = "permission_scope"
        for candidate in candidates:
            check = self.check_chunk(
                workspace_id=workspace_id,
                chunk=candidate.source_chunk,
                source_object_allowlist=source_object_allowlist,
            )
            if check.decision == "allowed":
                allowed.append(candidate)
            else:
                denied_count += 1
                reason = check.reason
        exclusions: dict[str, int | str] = {"excluded_count": denied_count}
        if denied_count:
            exclusions["reason"] = reason
        return PermissionFilterResult(candidates=allowed, exclusions=exclusions)

    def _matches_any_scope(
        self, chunk: SourceChunk, scopes: list[PermissionScope]
    ) -> bool:
        return any(_scope_matches_chunk(scope, chunk) for scope in scopes)


def _scope_matches_chunk(scope: PermissionScope, chunk: SourceChunk) -> bool:
    metadata = chunk.metadata_json
    object_type = str(metadata.get("object_type", ""))
    if scope.provider == "slack" and scope.scope_type == "slack_channel":
        channel_hash = metadata.get("channel_id_hash")
        return isinstance(channel_hash, str) and channel_hash == scope.external_id_hash
    if scope.provider == "linear" and scope.scope_type == "linear_team":
        return _metadata_id_matches_scope(scope, metadata.get("team_id"))
    if scope.provider == "linear" and scope.scope_type == "linear_project":
        return _metadata_id_matches_scope(scope, metadata.get("project_id"))
    if scope.provider == "github" and scope.scope_type == "github_repository":
        return _metadata_id_matches_scope(scope, metadata.get("repo_id"))
    if scope.provider == "repo_docs" and scope.scope_type == "repo_docs_root":
        repo_id = metadata.get("repo_id")
        path = metadata.get("path")
        scope_root = scope.metadata_json.get("path_prefix")
        return (
            object_type == "repo_doc"
            and isinstance(repo_id, str)
            and isinstance(path, str)
            and isinstance(scope_root, str)
            and _metadata_id_matches_scope(scope, repo_id)
            and path.startswith(scope_root)
        )
    return False


def _metadata_id_matches_scope(scope: PermissionScope, value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return (
        scope_external_id_hash(scope.provider, scope.scope_type, value)
        == scope.external_id_hash
    )
