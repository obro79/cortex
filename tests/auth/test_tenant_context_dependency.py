from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from cortex.auth.dependencies import (
    AUTH_EMAIL_HEADER,
    SESSION_ID_HEADER,
    require_tenant_context,
)
from cortex.config import Settings
from cortex.tenancy import (
    InMemoryTenantRepository,
    SqlAlchemyTenantRepository,
    TenantContext,
)
from cortex.ui.auth import ACTOR_ID_HEADER, ROLES_HEADER, WORKSPACE_ID_HEADER

TENANT_CONTEXT_DEPENDENCY = Depends(require_tenant_context)


def test_public_auth_dependency_resolves_active_workspace_context() -> None:
    app, repo, workspace_id = _app_with_owner_context()
    client = TestClient(app)

    response = client.get(
        "/context",
        headers={
            AUTH_EMAIL_HEADER: "owner@example.com",
            WORKSPACE_ID_HEADER: workspace_id,
            SESSION_ID_HEADER: "sess_public",
            "x-request-id": "trace_public",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "organization_id": next(iter(repo.organizations)),
        "workspace_id": workspace_id,
        "user_id": next(iter(repo.users)),
        "role": "owner",
        "session_id": "sess_public",
        "trace_id": "trace_public",
    }


def test_public_auth_dependency_denies_cross_workspace_access() -> None:
    app, _, workspace_id = _app_with_owner_context()
    repo = app.state.tenant_repository
    other_user = repo.upsert_user(
        auth_provider="local",
        auth_subject="other@example.com",
        email="other@example.com",
    )
    _, other_workspace, _ = repo.create_organization_with_workspace(
        user_id=other_user.id,
        organization_name="Other",
        workspace_name="Other",
        workspace_slug="other",
    )
    client = TestClient(app)

    response = client.get(
        "/context",
        headers={
            AUTH_EMAIL_HEADER: "owner@example.com",
            WORKSPACE_ID_HEADER: other_workspace.id,
        },
    )

    assert workspace_id != other_workspace.id
    assert response.status_code == 403
    assert response.json()["detail"] == "workspace access denied"


def test_public_auth_dependency_rejects_internal_actor_headers() -> None:
    app, _, workspace_id = _app_with_owner_context()
    client = TestClient(app)

    response = client.get(
        "/context",
        headers={
            AUTH_EMAIL_HEADER: "owner@example.com",
            WORKSPACE_ID_HEADER: workspace_id,
            ACTOR_ID_HEADER: "internal_actor",
            ROLES_HEADER: "workspace_admin",
        },
    )

    assert response.status_code == 401
    assert "internal actor headers" in response.json()["detail"]


def test_public_auth_dependency_requires_public_auth_enabled() -> None:
    app, _, workspace_id = _app_with_owner_context(public_auth_enabled=False)
    client = TestClient(app)

    response = client.get(
        "/context",
        headers={
            AUTH_EMAIL_HEADER: "owner@example.com",
            WORKSPACE_ID_HEADER: workspace_id,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "public auth is disabled"


def test_create_app_wires_sql_tenant_repository_for_sql_public_auth() -> None:
    from cortex.api.app import create_app

    app = create_app(
        Settings(
            cortex_public_auth_enabled=True,
            cortex_state_backend="sql",
            database_url="postgresql+asyncpg://localhost/cortex",
        )
    )

    assert isinstance(app.state.tenant_repository, SqlAlchemyTenantRepository)


def _app_with_owner_context(
    *, public_auth_enabled: bool = True
) -> tuple[FastAPI, InMemoryTenantRepository, str]:
    app = FastAPI()
    app.state.settings = Settings.model_construct(
        cortex_public_auth_enabled=public_auth_enabled,
        cortex_auth_provider="local",
    )
    repo = InMemoryTenantRepository()
    user = repo.upsert_user(
        auth_provider="local",
        auth_subject="owner@example.com",
        email="owner@example.com",
    )
    _, workspace, _ = repo.create_organization_with_workspace(
        user_id=user.id,
        organization_name="Acme",
        workspace_name="Engineering",
        workspace_slug="engineering",
    )
    app.state.tenant_repository = repo

    @app.get("/context")
    def context_route(
        context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
    ) -> dict[str, str | None]:
        return {
            "organization_id": context.organization_id,
            "workspace_id": context.workspace_id,
            "user_id": context.user_id,
            "role": context.role.value,
            "session_id": context.session_id,
            "trace_id": context.trace_id,
        }

    return app, repo, workspace.id
