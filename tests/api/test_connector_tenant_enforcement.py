from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.auth.dependencies import AUTH_EMAIL_HEADER
from cortex.billing import BillingStatus, SubscriptionStatus
from cortex.config import Settings
from cortex.tenancy import MembershipRole
from cortex.ui.auth import WORKSPACE_ID_HEADER


def test_github_source_selection_requires_tenant_context_and_plan_capacity() -> None:
    app = create_app(
        Settings(
            cortex_github_connector_enabled=True,
            cortex_public_auth_enabled=True,
        )
    )
    owner_headers = _seed_member(
        app,
        email="owner@example.com",
        role=MembershipRole.OWNER,
        with_trial=True,
    )
    client = TestClient(app)

    missing_auth = client.post(
        "/connectors/github/sources/select",
        json={"workspace_id": owner_headers[WORKSPACE_ID_HEADER], "repos": []},
    )
    allowed = client.post(
        "/connectors/github/sources/select",
        json={
            "workspace_id": owner_headers[WORKSPACE_ID_HEADER],
            "repos": [{"id": "repo_1"}, {"id": "repo_2"}],
        },
        headers=owner_headers,
    )
    denied_workspace = client.post(
        "/connectors/github/sources/select",
        json={"workspace_id": "ws_other", "repos": [{"id": "repo_3"}]},
        headers=owner_headers,
    )

    assert missing_auth.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json()["selected"] == [{"id": "repo_1"}, {"id": "repo_2"}]
    assert denied_workspace.status_code == 403


def test_linear_source_selection_denies_member_role() -> None:
    app = create_app(
        Settings(
            cortex_linear_connector_enabled=True,
            cortex_public_auth_enabled=True,
        )
    )
    member_headers = _seed_member(
        app,
        email="member@example.com",
        role=MembershipRole.MEMBER,
        with_trial=True,
    )
    client = TestClient(app)

    response = client.post(
        "/connectors/linear/sources/select",
        json={
            "workspace_id": member_headers[WORKSPACE_ID_HEADER],
            "sources": [{"id": "team_1", "type": "team"}],
        },
        headers=member_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "missing_permission"


def test_repo_docs_source_selection_enforces_invite_only_plan() -> None:
    app = create_app(
        Settings(
            cortex_repo_docs_connector_enabled=True,
            cortex_public_auth_enabled=True,
        )
    )
    owner_headers = _seed_member(
        app,
        email="owner@example.com",
        role=MembershipRole.OWNER,
        with_trial=False,
    )
    client = TestClient(app)

    response = client.post(
        "/connectors/repo-docs/sources/select",
        json={
            "workspace_id": owner_headers[WORKSPACE_ID_HEADER],
            "roots": [{"path": "docs"}],
        },
        headers=owner_headers,
    )

    assert response.status_code == 402
    assert response.json()["detail"]["reason"] == "plan_limit_exceeded"


def _seed_member(
    app: FastAPI,
    *,
    email: str,
    role: MembershipRole,
    with_trial: bool,
) -> dict[str, str]:
    repo = app.state.tenant_repository
    user = repo.upsert_user(
        auth_provider="local",
        auth_subject=email,
        email=email,
    )
    organization, workspace, membership = repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug=email.split("@")[0],
    )
    repo.memberships[membership.id] = replace(membership, role=role)
    if with_trial:
        customer = app.state.billing_repository.ensure_customer(
            organization_id=organization.id,
            status=BillingStatus.TRIALING,
        )
        app.state.billing_repository.upsert_subscription(
            organization_id=organization.id,
            billing_customer_id=customer.id,
            plan_id="free_trial",
            status=SubscriptionStatus.TRIALING,
        )
    return {
        AUTH_EMAIL_HEADER: email,
        WORKSPACE_ID_HEADER: workspace.id,
    }
