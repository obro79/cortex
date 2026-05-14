from cortex.tenancy import MembershipRole, TenantContext


def test_tenant_context_maps_owner_to_workspace_admin_role() -> None:
    context = TenantContext(
        organization_id="org_1",
        workspace_id="ws_1",
        user_id="usr_1",
        membership_id="mem_1",
        role=MembershipRole.OWNER,
    )

    assert context.roles == frozenset({"owner", "workspace_admin"})
    assert context.is_workspace_admin


def test_tenant_context_keeps_member_non_admin() -> None:
    context = TenantContext(
        organization_id="org_1",
        workspace_id="ws_1",
        user_id="usr_1",
        membership_id="mem_1",
        role=MembershipRole.MEMBER,
    )

    assert context.roles == frozenset({"member"})
    assert not context.is_workspace_admin
