from cortex.connectors.github.service import GitHubConnectorServices
from cortex.connectors.linear.service import LinearConnectorServices
from cortex.connectors.repo_docs.service import RepoDocsConnectorServices
from cortex.connectors.setup import (
    SourceSelectionService,
    build_connector_setup_service,
)
from cortex.security.admin_auth import AdminActor
from cortex.security.audit import InMemoryAuditLogRepository
from cortex.security.redaction import REDACTED


def test_connector_overview_normalizes_health_and_data_read_explanations() -> None:
    service = build_connector_setup_service(
        github=GitHubConnectorServices(app_configured=True, repo_ids={"repo_1"}),
        linear=LinearConnectorServices(api_token_configured=False),
        repo_docs=RepoDocsConnectorServices(roots={"docs"}, hashes={"docs/a.md": "h"}),
    )
    actor = AdminActor(
        actor_id="usr_1",
        workspace_id="ws_1",
        roles=frozenset({"workspace_admin"}),
    )

    overview = service.overview(workspace_id="ws_1", actor=actor)

    providers = {item["provider"]: item for item in overview["providers"]}
    assert providers["github"]["health"]["auth_status"] == "active"
    assert providers["github"]["health"]["selected_source_count"] == 1
    assert providers["github"]["can_admin"] is True
    assert "Selected repository issues" in providers["github"][
        "data_read_explanation"
    ][0]
    assert providers["linear"]["health"]["auth_status"] == "missing_token"
    assert providers["repo_docs"]["health"]["selected_root_count"] == 1


def test_connector_action_denies_non_admin_and_audits_without_target_leak() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = build_connector_setup_service(
        github=GitHubConnectorServices(),
        audit_log=audit_log,
    )
    actor = AdminActor(
        actor_id="usr_2",
        workspace_id="ws_1",
        roles=frozenset({"member"}),
    )

    result = service.require_action(
        workspace_id="ws_1",
        actor=actor,
        provider="github",
        action="setup",
        metadata_json={
            "installation_token": "ghs_secret",
            "private_url": "https://github.com/private/repo",
        },
    )

    record = audit_log.list_for_workspace("ws_1")[0]
    assert result.allowed is False
    assert result.reason == "missing_admin_role"
    assert record.decision == "denied"
    assert record.target_id_hash is not None
    assert record.metadata_json["installation_token"] == REDACTED
    assert record.metadata_json["private_url"] == REDACTED


def test_source_selection_requires_workspace_admin() -> None:
    audit_log = InMemoryAuditLogRepository()
    setup = build_connector_setup_service(
        linear=LinearConnectorServices(),
        audit_log=audit_log,
    )
    selection = SourceSelectionService(setup)
    actor = AdminActor(
        actor_id="usr_1",
        workspace_id="ws_1",
        roles=frozenset({"workspace_admin"}),
    )

    result = selection.require_source_selection(
        workspace_id="ws_1",
        actor=actor,
        provider="linear",
        source_count=2,
        metadata_json={"api_token": "lin_secret"},
    )

    assert result.allowed is True
    assert result.action == "source_select"
    record = audit_log.list_for_workspace("ws_1")[0]
    assert record.decision == "allowed"
    assert record.metadata_json["api_token"] == REDACTED


def test_connector_action_denies_workspace_mismatch() -> None:
    service = build_connector_setup_service(github=GitHubConnectorServices())
    actor = AdminActor(
        actor_id="usr_1",
        workspace_id="ws_other",
        roles=frozenset({"workspace_admin"}),
    )

    result = service.require_action(
        workspace_id="ws_1",
        actor=actor,
        provider="github",
        action="revoke",
    )

    assert result.allowed is False
    assert result.reason == "workspace_mismatch"
