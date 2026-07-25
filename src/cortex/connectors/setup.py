from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cortex.security.admin_auth import AdminActor, AdminAuthorizationService
from cortex.security.audit import InMemoryAuditLogRepository
from cortex.security.redaction import redact_mapping
from cortex.tenancy.rbac import Permission, RolePermissionService

CONNECTOR_ACTIONS = frozenset(
    {
        "setup",
        "source_select",
        "reauth",
        "revoke",
        "backfill_retry",
    }
)

DATA_READ_EXPLANATIONS: dict[str, tuple[str, ...]] = {
    "slack": (
        "Selected channel messages and thread replies",
        "Message metadata needed for citations and freshness",
        "File metadata and extractable text when file ingestion is enabled",
    ),
    "github": (
        "Selected repository issues, pull requests, commits, and comments",
        "Repository metadata needed for citations and source health",
    ),
    "linear": (
        "Selected team or project issues and comments",
        "Issue metadata needed for status, ownership, and citations",
    ),
    "repo_docs": (
        "Selected repository documentation paths",
        "Document content hashes and metadata needed for indexing",
    ),
}


class ConnectorProvider(Protocol):
    def health(self, workspace_id: str) -> dict[str, object]: ...


@dataclass(frozen=True)
class ConnectorSetupProvider:
    provider: str
    display_name: str
    service: ConnectorProvider
    setup_enabled: bool = True

    def data_read_explanation(self) -> tuple[str, ...]:
        return DATA_READ_EXPLANATIONS.get(self.provider, ())


@dataclass(frozen=True)
class ConnectorActionResult:
    allowed: bool
    provider: str
    action: str
    reason: str
    metadata_json: dict[str, object]


class ConnectorSetupService:
    def __init__(
        self,
        *,
        providers: list[ConnectorSetupProvider],
        audit_log: InMemoryAuditLogRepository | None = None,
    ) -> None:
        self.providers = {provider.provider: provider for provider in providers}
        self.audit_log = audit_log or InMemoryAuditLogRepository()
        self.authorization = AdminAuthorizationService(self.audit_log)
        self.permissions = RolePermissionService()

    def overview(
        self, *, workspace_id: str, actor: AdminActor | None
    ) -> dict[str, object]:
        return {
            "workspace_id": workspace_id,
            "providers": [
                self._provider_overview(
                    provider=provider,
                    workspace_id=workspace_id,
                    actor=actor,
                )
                for provider in sorted(
                    self.providers.values(), key=lambda item: item.provider
                )
            ],
        }

    def health(self, *, workspace_id: str, provider: str) -> dict[str, object]:
        setup_provider = self._provider(provider)
        return redact_mapping(setup_provider.service.health(workspace_id))

    def require_action(
        self,
        *,
        workspace_id: str,
        actor: AdminActor | None,
        provider: str,
        action: str,
        metadata_json: dict[str, object] | None = None,
    ) -> ConnectorActionResult:
        if action not in CONNECTOR_ACTIONS:
            raise ValueError(f"unsupported connector action: {action}")
        setup_provider = self._provider(provider)
        permission = (
            Permission.SOURCE_SELECT
            if action == "source_select"
            else Permission.CONNECTOR_SETUP
        )
        role_allowed = self._actor_has_permission(
            actor=actor,
            permission=permission,
        )
        auth = self.authorization.require_admin(
            workspace_id=workspace_id,
            actor=actor,
            action=f"connector.{action}",
            target_type="connector_provider",
            target_id=provider,
            metadata_json={
                "provider": provider,
                "action": action,
                **(metadata_json or {}),
            },
        )
        allowed = auth.allowed and role_allowed
        reason = auth.reason if auth.allowed else auth.reason
        if auth.allowed and not role_allowed:
            reason = "missing_permission"
        return ConnectorActionResult(
            allowed=allowed,
            provider=setup_provider.provider,
            action=action,
            reason=reason,
            metadata_json=redact_mapping(metadata_json or {}),
        )

    def _provider_overview(
        self,
        *,
        provider: ConnectorSetupProvider,
        workspace_id: str,
        actor: AdminActor | None,
    ) -> dict[str, object]:
        action = self.authorization.require_admin(
            workspace_id=workspace_id,
            actor=actor,
            action="connector.view",
            target_type="connector_provider",
            target_id=provider.provider,
            metadata_json={"provider": provider.provider},
        )
        health = self.health(workspace_id=workspace_id, provider=provider.provider)
        return {
            "provider": provider.provider,
            "display_name": provider.display_name,
            "setup_enabled": provider.setup_enabled,
            "can_admin": action.allowed,
            "admin_reason": action.reason,
            "data_read_explanation": list(provider.data_read_explanation()),
            "health": health,
        }

    def _provider(self, provider: str) -> ConnectorSetupProvider:
        try:
            return self.providers[provider]
        except KeyError as error:
            raise ValueError(f"unsupported connector provider: {provider}") from error

    def _actor_has_permission(
        self, *, actor: AdminActor | None, permission: Permission
    ) -> bool:
        if actor is None:
            return False
        for role in actor.roles:
            if role == "workspace_admin":
                role = "admin"
            try:
                decision = self.permissions.decide(
                    role=role,
                    permission=permission,
                    approval_granted=True,
                )
            except ValueError:
                continue
            if decision.allowed:
                return True
        return False


class SourceSelectionService:
    def __init__(self, setup: ConnectorSetupService) -> None:
        self.setup = setup

    def require_source_selection(
        self,
        *,
        workspace_id: str,
        actor: AdminActor | None,
        provider: str,
        source_count: int,
        metadata_json: dict[str, object] | None = None,
    ) -> ConnectorActionResult:
        return self.setup.require_action(
            workspace_id=workspace_id,
            actor=actor,
            provider=provider,
            action="source_select",
            metadata_json={
                "source_count": source_count,
                **(metadata_json or {}),
            },
        )


def build_connector_setup_service(
    *,
    slack: ConnectorProvider | None = None,
    github: ConnectorProvider | None = None,
    linear: ConnectorProvider | None = None,
    repo_docs: ConnectorProvider | None = None,
    audit_log: InMemoryAuditLogRepository | None = None,
) -> ConnectorSetupService:
    providers: list[ConnectorSetupProvider] = []
    if slack is not None:
        providers.append(ConnectorSetupProvider("slack", "Slack", slack))
    if github is not None:
        providers.append(ConnectorSetupProvider("github", "GitHub", github))
    if linear is not None:
        providers.append(ConnectorSetupProvider("linear", "Linear", linear))
    if repo_docs is not None:
        providers.append(ConnectorSetupProvider("repo_docs", "Repo Docs", repo_docs))
    return ConnectorSetupService(providers=providers, audit_log=audit_log)
