from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, status

from cortex.auth.provider import LocalAuthProvider
from cortex.config import Settings
from cortex.tenancy import InMemoryTenantRepository, TenantContext, TenantRepository
from cortex.ui.auth import (
    ACTOR_ID_HEADER,
    ROLES_HEADER,
    TRACE_ID_HEADER,
    WORKSPACE_ID_HEADER,
)

AUTH_EMAIL_HEADER = "x-cortex-auth-email"
AUTH_DISPLAY_NAME_HEADER = "x-cortex-auth-display-name"
SESSION_ID_HEADER = "x-cortex-public-session-id"


def require_tenant_context(request: Request) -> TenantContext:
    settings = _settings(request)
    if not settings.cortex_public_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="public auth is disabled",
        )
    _reject_internal_actor_shortcut(request)

    workspace_id = _required_header(request, WORKSPACE_ID_HEADER)
    email = _required_header(request, AUTH_EMAIL_HEADER)
    display_name = request.headers.get(AUTH_DISPLAY_NAME_HEADER)
    session_id = request.headers.get(SESSION_ID_HEADER)
    trace_id = request.headers.get(TRACE_ID_HEADER) or secrets.token_hex(16)

    provider = LocalAuthProvider()
    identity = provider.identity_from_verified_email(
        email=email,
        display_name=display_name,
    )
    repository = _tenant_repository(request)
    user = repository.upsert_user(
        auth_provider=identity.provider,
        auth_subject=identity.subject,
        email=identity.email,
        display_name=identity.display_name,
        email_verified_at=identity.email_verified_at,
    )
    context = repository.resolve_context(
        user_id=user.id,
        workspace_id=workspace_id,
        session_id=session_id,
        trace_id=trace_id,
    )
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="workspace access denied",
        )
    return context


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are not configured")
    return settings


def _tenant_repository(request: Request) -> TenantRepository:
    repository = getattr(request.app.state, "tenant_repository", None)
    if repository is None:
        repository = InMemoryTenantRepository()
        request.app.state.tenant_repository = repository
    return repository


def _required_header(request: Request, name: str) -> str:
    value = request.headers.get(name, "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{name} header is required",
        )
    return value


def _reject_internal_actor_shortcut(request: Request) -> None:
    forbidden_headers = {
        ACTOR_ID_HEADER,
        ROLES_HEADER,
    }
    if any(request.headers.get(header) for header in forbidden_headers):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="internal actor headers are not accepted for public auth",
        )
