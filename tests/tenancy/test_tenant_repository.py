from datetime import UTC, datetime, timedelta

import pytest

from cortex.auth.provider import LocalAuthProvider
from cortex.tenancy import (
    InMemoryTenantRepository,
    InvitationStatus,
    MembershipRole,
)


def test_first_workspace_setup_creates_owner_context() -> None:
    repo = InMemoryTenantRepository()
    identity = LocalAuthProvider().identity_from_verified_email(
        email="Owner@Example.com", display_name="Owner"
    )

    user = repo.upsert_user(
        auth_provider=identity.provider,
        auth_subject=identity.subject,
        email=identity.email,
        display_name=identity.display_name,
        email_verified_at=identity.email_verified_at,
    )
    organization, workspace, membership = repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )

    context = repo.resolve_context(
        user_id=user.id,
        workspace_id=workspace.id,
        session_id="sess_1",
        trace_id="trace_1",
    )

    assert organization.created_by_user_id == user.id
    assert membership.role == MembershipRole.OWNER
    assert context is not None
    assert context.organization_id == organization.id
    assert context.workspace_id == workspace.id
    assert context.user_id == user.id
    assert context.is_workspace_admin
    assert "workspace_admin" in context.roles


def test_context_resolution_denies_cross_workspace_access() -> None:
    repo = InMemoryTenantRepository()
    user_a = repo.upsert_user(
        auth_provider="local",
        auth_subject="a@example.com",
        email="a@example.com",
    )
    user_b = repo.upsert_user(
        auth_provider="local",
        auth_subject="b@example.com",
        email="b@example.com",
    )
    _, workspace_a, _ = repo.create_organization_with_workspace(
        user_id=user_a.id,
        organization_name="A",
        workspace_name="A Workspace",
        workspace_slug="a",
    )
    _, workspace_b, _ = repo.create_organization_with_workspace(
        user_id=user_b.id,
        organization_name="B",
        workspace_name="B Workspace",
        workspace_slug="b",
    )

    assert repo.resolve_context(user_id=user_a.id, workspace_id=workspace_a.id)
    assert repo.resolve_context(user_id=user_a.id, workspace_id=workspace_b.id) is None


def test_invite_acceptance_creates_member_context() -> None:
    repo = InMemoryTenantRepository()
    owner = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    teammate = repo.upsert_user(
        auth_provider="local",
        auth_subject="teammate@example.com",
        email="teammate@example.com",
    )
    organization, workspace, _ = repo.create_organization_with_workspace(
        user_id=owner.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    invitation = repo.create_invitation(
        organization_id=organization.id,
        workspace_id=workspace.id,
        email="teammate@example.com",
        role=MembershipRole.MEMBER,
        invited_by_user_id=owner.id,
        token_hash="sha256:invite-token",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    membership = repo.accept_invitation(
        token_hash=invitation.token_hash, user_id=teammate.id
    )
    accepted_invitation = repo.invitations[invitation.id]
    context = repo.resolve_context(user_id=teammate.id, workspace_id=workspace.id)

    assert membership is not None
    assert membership.role == MembershipRole.MEMBER
    assert accepted_invitation.status == InvitationStatus.ACCEPTED
    assert accepted_invitation.accepted_by_user_id == teammate.id
    assert context is not None
    assert not context.is_workspace_admin


def test_non_admin_cannot_invite_teammates() -> None:
    repo = InMemoryTenantRepository()
    owner = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    member = repo.upsert_user(
        auth_provider="local",
        auth_subject="member@example.com",
        email="member@example.com",
    )
    organization, workspace, _ = repo.create_organization_with_workspace(
        user_id=owner.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    invitation = repo.create_invitation(
        organization_id=organization.id,
        workspace_id=workspace.id,
        email="member@example.com",
        role=MembershipRole.MEMBER,
        invited_by_user_id=owner.id,
        token_hash="sha256:first-invite",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    repo.accept_invitation(token_hash=invitation.token_hash, user_id=member.id)

    with pytest.raises(PermissionError):
        repo.create_invitation(
            organization_id=organization.id,
            workspace_id=workspace.id,
            email="other@example.com",
            role=MembershipRole.MEMBER,
            invited_by_user_id=member.id,
            token_hash="sha256:second-invite",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )


def test_expired_invitation_cannot_be_accepted() -> None:
    repo = InMemoryTenantRepository()
    owner = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    teammate = repo.upsert_user(
        auth_provider="local",
        auth_subject="teammate@example.com",
        email="teammate@example.com",
    )
    organization, workspace, _ = repo.create_organization_with_workspace(
        user_id=owner.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    invitation = repo.create_invitation(
        organization_id=organization.id,
        workspace_id=workspace.id,
        email="teammate@example.com",
        role=MembershipRole.MEMBER,
        invited_by_user_id=owner.id,
        token_hash="sha256:expired-token",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert (
        repo.accept_invitation(token_hash=invitation.token_hash, user_id=teammate.id)
        is None
    )
    assert repo.resolve_context(user_id=teammate.id, workspace_id=workspace.id) is None


def test_legal_consent_is_recorded_by_user_and_version() -> None:
    repo = InMemoryTenantRepository()
    user = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    organization, workspace, _ = repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    accepted_at = datetime.now(UTC)

    consent = repo.record_legal_consent(
        user_id=user.id,
        organization_id=organization.id,
        workspace_id=workspace.id,
        consent_type="terms",
        version="terms-v1",
        accepted_at=accepted_at,
    )

    assert consent.user_id == user.id
    assert consent.organization_id == organization.id
    assert consent.workspace_id == workspace.id
    assert consent.accepted_at == accepted_at
