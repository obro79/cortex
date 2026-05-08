from __future__ import annotations

from dataclasses import dataclass

from cortex.security.audit import InMemoryAuditLogRepository

ADMIN_ROLES = frozenset({"workspace_admin", "security_admin"})


@dataclass(frozen=True)
class AdminActor:
    actor_id: str
    workspace_id: str
    roles: frozenset[str]
    disabled: bool = False


@dataclass(frozen=True)
class AdminAuthorizationResult:
    allowed: bool
    reason: str


class AdminAuthorizationService:
    def __init__(self, audit_log: InMemoryAuditLogRepository) -> None:
        self.audit_log = audit_log

    def require_admin(
        self,
        *,
        workspace_id: str,
        actor: AdminActor | None,
        action: str,
        target_type: str,
        target_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> AdminAuthorizationResult:
        reason = self._deny_reason(workspace_id=workspace_id, actor=actor)
        allowed = reason is None
        result = AdminAuthorizationResult(
            allowed=allowed,
            reason="allowed" if allowed else reason or "denied",
        )
        self.audit_log.append(
            workspace_id=workspace_id,
            actor_id=actor.actor_id if actor is not None else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            decision="allowed" if allowed else "denied",
            reason=result.reason,
            metadata_json=metadata_json,
        )
        return result

    def _deny_reason(
        self, *, workspace_id: str, actor: AdminActor | None
    ) -> str | None:
        if actor is None:
            return "missing_actor"
        if actor.disabled:
            return "actor_disabled"
        if actor.workspace_id != workspace_id:
            return "workspace_mismatch"
        if not actor.roles.intersection(ADMIN_ROLES):
            return "missing_admin_role"
        return None
