from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TenantStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SECURITY_ADMIN = "security_admin"
    BILLING_ADMIN = "billing_admin"
    MEMBER = "member"
    VIEWER = "viewer"


ADMIN_ROLES = frozenset(
    {
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
        MembershipRole.SECURITY_ADMIN,
        MembershipRole.BILLING_ADMIN,
    }
)


@dataclass(frozen=True)
class Organization:
    id: str
    display_name: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Workspace:
    id: str
    organization_id: str
    slug: str
    display_name: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class User:
    id: str
    auth_provider: str
    auth_subject: str
    email: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None
    email_verified_at: datetime | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Membership:
    id: str
    organization_id: str
    workspace_id: str
    user_id: str
    role: MembershipRole
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime
    invited_by_user_id: str | None = None


@dataclass(frozen=True)
class Invitation:
    id: str
    organization_id: str
    workspace_id: str
    email: str
    role: MembershipRole
    status: InvitationStatus
    token_hash: str
    invited_by_user_id: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    accepted_by_user_id: str | None = None
    accepted_at: datetime | None = None


@dataclass(frozen=True)
class LegalConsent:
    id: str
    user_id: str
    consent_type: str
    version: str
    accepted_at: datetime
    created_at: datetime
    organization_id: str | None = None
    workspace_id: str | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TenantContext:
    organization_id: str
    workspace_id: str
    user_id: str
    membership_id: str
    role: MembershipRole
    session_id: str | None = None
    trace_id: str | None = None

    @property
    def roles(self) -> frozenset[str]:
        mapped = {self.role.value}
        if self.role in ADMIN_ROLES:
            mapped.add("workspace_admin")
        return frozenset(mapped)

    @property
    def is_workspace_admin(self) -> bool:
        return self.role in ADMIN_ROLES
