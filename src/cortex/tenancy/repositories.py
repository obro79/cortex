from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from cortex.ingestion.payloads import sha256_digest
from cortex.tenancy.models import (
    Invitation,
    InvitationStatus,
    LegalConsent,
    Membership,
    MembershipRole,
    MembershipStatus,
    Organization,
    TenantContext,
    TenantStatus,
    User,
    UserStatus,
    Workspace,
)


class TenantRepository(Protocol):
    def upsert_user(
        self,
        *,
        auth_provider: str,
        auth_subject: str,
        email: str,
        display_name: str | None = None,
        email_verified_at: datetime | None = None,
    ) -> User: ...

    def create_organization_with_workspace(
        self,
        *,
        user_id: str,
        organization_name: str,
        workspace_name: str,
        workspace_slug: str,
    ) -> tuple[Organization, Workspace, Membership]: ...

    def resolve_context(
        self,
        *,
        user_id: str,
        workspace_id: str,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> TenantContext | None: ...

    def create_invitation(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        email: str,
        role: MembershipRole,
        invited_by_user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> Invitation: ...

    def accept_invitation(
        self, *, token_hash: str, user_id: str, accepted_at: datetime | None = None
    ) -> Membership | None: ...

    def record_legal_consent(
        self,
        *,
        user_id: str,
        consent_type: str,
        version: str,
        accepted_at: datetime,
        organization_id: str | None = None,
        workspace_id: str | None = None,
    ) -> LegalConsent: ...


class InMemoryTenantRepository:
    def __init__(self) -> None:
        self.organizations: dict[str, Organization] = {}
        self.workspaces: dict[str, Workspace] = {}
        self.users: dict[str, User] = {}
        self.memberships: dict[str, Membership] = {}
        self.invitations: dict[str, Invitation] = {}
        self.legal_consents: dict[str, LegalConsent] = {}

    def upsert_user(
        self,
        *,
        auth_provider: str,
        auth_subject: str,
        email: str,
        display_name: str | None = None,
        email_verified_at: datetime | None = None,
    ) -> User:
        now = datetime.now(UTC)
        existing = self._user_by_subject(auth_provider, auth_subject)
        if existing is not None:
            user = replace(
                existing,
                email=email.lower(),
                display_name=display_name,
                email_verified_at=email_verified_at,
                updated_at=now,
            )
            self.users[user.id] = user
            return user
        user = User(
            id=_stable_id("usr", auth_provider, auth_subject),
            auth_provider=auth_provider,
            auth_subject=auth_subject,
            email=email.lower(),
            display_name=display_name,
            status=UserStatus.ACTIVE,
            email_verified_at=email_verified_at,
            created_at=now,
            updated_at=now,
        )
        self.users[user.id] = user
        return user

    def create_organization_with_workspace(
        self,
        *,
        user_id: str,
        organization_name: str,
        workspace_name: str,
        workspace_slug: str,
    ) -> tuple[Organization, Workspace, Membership]:
        if user_id not in self.users:
            raise ValueError("user does not exist")
        now = datetime.now(UTC)
        organization = Organization(
            id=_stable_id("org", user_id, organization_name),
            display_name=organization_name,
            status=TenantStatus.ACTIVE,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        workspace = Workspace(
            id=_stable_id("ws", organization.id, workspace_slug),
            organization_id=organization.id,
            slug=workspace_slug,
            display_name=workspace_name,
            status=TenantStatus.ACTIVE,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        membership = Membership(
            id=_stable_id("mem", organization.id, workspace.id, user_id),
            organization_id=organization.id,
            workspace_id=workspace.id,
            user_id=user_id,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self.organizations[organization.id] = organization
        self.workspaces[workspace.id] = workspace
        self.memberships[membership.id] = membership
        return organization, workspace, membership

    def resolve_context(
        self,
        *,
        user_id: str,
        workspace_id: str,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> TenantContext | None:
        user = self.users.get(user_id)
        workspace = self.workspaces.get(workspace_id)
        if (
            user is None
            or workspace is None
            or user.status != UserStatus.ACTIVE
            or workspace.status != TenantStatus.ACTIVE
        ):
            return None
        organization = self.organizations.get(workspace.organization_id)
        if organization is None or organization.status != TenantStatus.ACTIVE:
            return None
        membership = self._active_membership(user_id, workspace_id)
        if membership is None:
            return None
        return TenantContext(
            organization_id=membership.organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            membership_id=membership.id,
            role=membership.role,
            session_id=session_id,
            trace_id=trace_id,
        )

    def create_invitation(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        email: str,
        role: MembershipRole,
        invited_by_user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> Invitation:
        inviter = self._active_membership(invited_by_user_id, workspace_id)
        if inviter is None or inviter.role not in {
            MembershipRole.OWNER,
            MembershipRole.ADMIN,
        }:
            raise PermissionError("workspace admin role required")
        if self.workspaces.get(workspace_id) is None:
            raise ValueError("workspace does not exist")
        now = datetime.now(UTC)
        invitation = Invitation(
            id=_stable_id("inv", workspace_id, email.lower(), token_hash),
            organization_id=organization_id,
            workspace_id=workspace_id,
            email=email.lower(),
            role=role,
            status=InvitationStatus.PENDING,
            token_hash=token_hash,
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self.invitations[invitation.id] = invitation
        return invitation

    def accept_invitation(
        self, *, token_hash: str, user_id: str, accepted_at: datetime | None = None
    ) -> Membership | None:
        now = accepted_at or datetime.now(UTC)
        invitation = self._pending_invitation(token_hash)
        if invitation is None or invitation.expires_at <= now:
            return None
        if user_id not in self.users:
            raise ValueError("user does not exist")
        existing = self._active_membership(user_id, invitation.workspace_id)
        accepted = replace(
            invitation,
            status=InvitationStatus.ACCEPTED,
            accepted_by_user_id=user_id,
            accepted_at=now,
            updated_at=now,
        )
        self.invitations[accepted.id] = accepted
        if existing is not None:
            return existing
        membership = Membership(
            id=_stable_id(
                "mem", invitation.organization_id, invitation.workspace_id, user_id
            ),
            organization_id=invitation.organization_id,
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            role=invitation.role,
            status=MembershipStatus.ACTIVE,
            invited_by_user_id=invitation.invited_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self.memberships[membership.id] = membership
        return membership

    def record_legal_consent(
        self,
        *,
        user_id: str,
        consent_type: str,
        version: str,
        accepted_at: datetime,
        organization_id: str | None = None,
        workspace_id: str | None = None,
    ) -> LegalConsent:
        consent = LegalConsent(
            id=_stable_id("consent", user_id, consent_type, version),
            user_id=user_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            consent_type=consent_type,
            version=version,
            accepted_at=accepted_at,
            created_at=accepted_at,
        )
        self.legal_consents[consent.id] = consent
        return consent

    def _user_by_subject(self, auth_provider: str, auth_subject: str) -> User | None:
        for user in self.users.values():
            if (
                user.auth_provider == auth_provider
                and user.auth_subject == auth_subject
            ):
                return user
        return None

    def _active_membership(
        self, user_id: str, workspace_id: str
    ) -> Membership | None:
        for membership in self.memberships.values():
            if (
                membership.user_id == user_id
                and membership.workspace_id == workspace_id
                and membership.status == MembershipStatus.ACTIVE
            ):
                return membership
        return None

    def _pending_invitation(self, token_hash: str) -> Invitation | None:
        for invitation in self.invitations.values():
            if (
                invitation.token_hash == token_hash
                and invitation.status == InvitationStatus.PENDING
            ):
                return invitation
        return None


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256_digest(":".join(parts).encode()).removeprefix("sha256:")[:24]
    return f"{prefix}_{digest}"
