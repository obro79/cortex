from cortex.tenancy import MembershipRole, Permission, RolePermissionService


def test_owner_has_every_permission() -> None:
    service = RolePermissionService()

    for permission in Permission:
        decision = service.decide(
            role=MembershipRole.OWNER,
            permission=permission,
            approval_granted=True,
        )
        assert decision.allowed is True


def test_billing_admin_cannot_manage_connectors_or_users() -> None:
    service = RolePermissionService()

    billing = service.decide(
        role=MembershipRole.BILLING_ADMIN,
        permission=Permission.BILLING_ADMIN,
    )
    connector = service.decide(
        role=MembershipRole.BILLING_ADMIN,
        permission=Permission.CONNECTOR_SETUP,
    )
    users = service.decide(
        role=MembershipRole.BILLING_ADMIN,
        permission=Permission.USER_MANAGE,
    )

    assert billing.allowed is True
    assert connector.allowed is False
    assert connector.reason == "missing_permission"
    assert users.allowed is False


def test_risky_actions_require_explicit_approval() -> None:
    service = RolePermissionService()

    blocked = service.decide(
        role=MembershipRole.SECURITY_ADMIN,
        permission=Permission.REINDEX,
    )
    allowed = service.decide(
        role=MembershipRole.SECURITY_ADMIN,
        permission=Permission.REINDEX,
        approval_granted=True,
    )

    assert blocked.allowed is False
    assert blocked.reason == "approval_required"
    assert blocked.approval_required is True
    assert allowed.allowed is True
    assert allowed.approval_required is True
