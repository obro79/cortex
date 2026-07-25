from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from hashlib import sha256

from fastapi import HTTPException, Request, status
from fastapi.responses import Response

from cortex.config import Settings
from cortex.security.admin_auth import AdminActor

ACTOR_ID_HEADER = "x-cortex-actor-id"
ROLES_HEADER = "x-cortex-actor-roles"
SESSION_ID_HEADER = "x-cortex-session-id"
WORKSPACE_ID_HEADER = "x-cortex-workspace-id"
CSRF_HEADER = "x-cortex-csrf-token"
TRACE_ID_HEADER = "x-request-id"
WORKSPACE_ID_COOKIE = "cortex_ui_workspace_id"
ACTOR_ID_COOKIE = "cortex_ui_actor_id"
ROLES_COOKIE = "cortex_ui_actor_roles"
SESSION_ID_COOKIE = "cortex_ui_session_id"


@dataclass(frozen=True)
class UiActorContext:
    actor_id: str
    workspace_id: str
    roles: frozenset[str]
    session_id: str
    trace_id: str
    csrf_token: str

    def admin_actor(self) -> AdminActor:
        return AdminActor(
            actor_id=self.actor_id,
            workspace_id=self.workspace_id,
            roles=self.roles,
        )


def resolve_ui_actor_context(request: Request) -> UiActorContext:
    settings = _settings(request)
    if not settings.cortex_ui_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if not settings.cortex_internal_admin_session_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ui session required",
        )

    workspace_id = _required_session_value(
        request, WORKSPACE_ID_HEADER, WORKSPACE_ID_COOKIE
    )
    actor_id = _required_session_value(request, ACTOR_ID_HEADER, ACTOR_ID_COOKIE)
    session_id = _required_session_value(request, SESSION_ID_HEADER, SESSION_ID_COOKIE)
    roles = _roles(
        request.headers.get(ROLES_HEADER) or request.cookies.get(ROLES_COOKIE, "")
    )
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ui actor role required",
        )

    trace_id = request.headers.get(TRACE_ID_HEADER) or secrets.token_hex(16)
    return UiActorContext(
        actor_id=actor_id,
        workspace_id=workspace_id,
        roles=roles,
        session_id=session_id,
        trace_id=trace_id,
        csrf_token=issue_csrf_token(
            settings=settings,
            workspace_id=workspace_id,
            actor_id=actor_id,
            session_id=session_id,
        ),
    )


def issue_csrf_token(
    *,
    settings: Settings,
    workspace_id: str,
    actor_id: str,
    session_id: str,
) -> str:
    message = f"{workspace_id}:{actor_id}:{session_id}".encode()
    return hmac.new(_csrf_secret(settings), message, sha256).hexdigest()


def require_csrf(request: Request, context: UiActorContext) -> None:
    provided = request.headers.get(CSRF_HEADER, "")
    if not hmac.compare_digest(provided, context.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid csrf token",
        )


def set_internal_session_cookies(
    response: Response,
    *,
    workspace_id: str,
    actor_id: str,
    roles: frozenset[str],
    session_id: str,
) -> None:
    _set_ui_cookie(response, WORKSPACE_ID_COOKIE, workspace_id)
    _set_ui_cookie(response, ACTOR_ID_COOKIE, actor_id)
    _set_ui_cookie(response, ROLES_COOKIE, ",".join(sorted(roles)))
    _set_ui_cookie(response, SESSION_ID_COOKIE, session_id)


def _set_ui_cookie(response: Response, key: str, value: str) -> None:
    response.set_cookie(
        key,
        value,
        httponly=True,
        secure=False,
        samesite="strict",
        path="/ui",
    )


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are not configured")
    return settings


def _csrf_secret(settings: Settings) -> bytes:
    secret = settings.cortex_ui_session_secret or settings.cortex_secret_encryption_key
    if not secret and settings.cortex_env in {"local", "test"}:
        secret = "local-ui-session-secret"
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ui session secret is not configured",
        )
    return secret.encode()


def _required_session_value(
    request: Request, header_name: str, cookie_name: str
) -> str:
    raw_value = request.headers.get(header_name) or request.cookies.get(cookie_name, "")
    value = raw_value.strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ui session required",
        )
    return value


def _roles(value: str) -> frozenset[str]:
    return frozenset(role.strip() for role in value.split(",") if role.strip())
