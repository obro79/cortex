from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cortex.tenancy.models import MembershipRole


class Permission(StrEnum):
    CONNECTOR_SETUP = "connector_setup"
    SOURCE_SELECT = "source_select"
    REPLAY_JOB = "replay_job"
    REINDEX = "reindex"
    REEMBED = "reembed"
    CANONICAL_APPROVE = "canonical_approve"
    BILLING_ADMIN = "billing_admin"
    USER_MANAGE = "user_manage"
    ROLE_MANAGE = "role_manage"
    SECURITY_REVIEW = "security_review"
    RETRIEVAL_READ = "retrieval_read"


RISKY_PERMISSIONS = frozenset(
    {
        Permission.REPLAY_JOB,
        Permission.REINDEX,
        Permission.REEMBED,
        Permission.ROLE_MANAGE,
    }
)


ROLE_PERMISSIONS: dict[MembershipRole, frozenset[Permission]] = {
    MembershipRole.OWNER: frozenset(Permission),
    MembershipRole.ADMIN: frozenset(
        {
            Permission.CONNECTOR_SETUP,
            Permission.SOURCE_SELECT,
            Permission.REPLAY_JOB,
            Permission.REINDEX,
            Permission.REEMBED,
            Permission.CANONICAL_APPROVE,
            Permission.USER_MANAGE,
            Permission.RETRIEVAL_READ,
        }
    ),
    MembershipRole.SECURITY_ADMIN: frozenset(
        {
            Permission.CONNECTOR_SETUP,
            Permission.SOURCE_SELECT,
            Permission.REPLAY_JOB,
            Permission.REINDEX,
            Permission.REEMBED,
            Permission.CANONICAL_APPROVE,
            Permission.USER_MANAGE,
            Permission.ROLE_MANAGE,
            Permission.SECURITY_REVIEW,
            Permission.RETRIEVAL_READ,
        }
    ),
    MembershipRole.BILLING_ADMIN: frozenset(
        {
            Permission.BILLING_ADMIN,
            Permission.RETRIEVAL_READ,
        }
    ),
    MembershipRole.MEMBER: frozenset(
        {
            Permission.CANONICAL_APPROVE,
            Permission.RETRIEVAL_READ,
        }
    ),
    MembershipRole.VIEWER: frozenset({Permission.RETRIEVAL_READ}),
}


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    role: MembershipRole
    permission: Permission
    reason: str
    approval_required: bool = False


class RolePermissionService:
    def decide(
        self,
        *,
        role: MembershipRole | str,
        permission: Permission | str,
        approval_granted: bool = False,
    ) -> PermissionDecision:
        resolved_role = MembershipRole(role)
        resolved_permission = Permission(permission)
        allowed = resolved_permission in ROLE_PERMISSIONS[resolved_role]
        if not allowed:
            return PermissionDecision(
                allowed=False,
                role=resolved_role,
                permission=resolved_permission,
                reason="missing_permission",
            )
        approval_required = resolved_permission in RISKY_PERMISSIONS
        if approval_required and not approval_granted:
            return PermissionDecision(
                allowed=False,
                role=resolved_role,
                permission=resolved_permission,
                reason="approval_required",
                approval_required=True,
            )
        return PermissionDecision(
            allowed=True,
            role=resolved_role,
            permission=resolved_permission,
            reason="allowed",
            approval_required=approval_required,
        )

    def permissions_for(self, role: MembershipRole | str) -> frozenset[Permission]:
        return ROLE_PERMISSIONS[MembershipRole(role)]
