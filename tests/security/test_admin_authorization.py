from cortex.security.admin_auth import AdminActor, AdminAuthorizationService
from cortex.security.audit import InMemoryAuditLogRepository
from cortex.security.redaction import REDACTED


def test_admin_authorization_allows_admin_and_audits_without_raw_target() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = AdminAuthorizationService(audit_log)
    actor = AdminActor(
        actor_id="actor_1",
        workspace_id="ws_1",
        roles=frozenset({"workspace_admin"}),
    )

    result = service.require_admin(
        workspace_id="ws_1",
        actor=actor,
        action="permission_scope.add",
        target_type="slack_channel",
        target_id="C123",
        metadata_json={"access_token": "xoxb-secret", "channel_id": "C123"},
    )

    assert result.allowed is True
    record = audit_log.list_for_workspace("ws_1")[0]
    assert record.decision == "allowed"
    assert record.target_id_hash is not None
    assert record.target_id_hash != "C123"
    assert record.metadata_json["access_token"] == REDACTED
    assert record.metadata_json["channel_id"] == "C123"


def test_admin_authorization_denies_non_admin_and_audits_denial() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = AdminAuthorizationService(audit_log)
    actor = AdminActor(
        actor_id="actor_2",
        workspace_id="ws_1",
        roles=frozenset({"member"}),
    )

    result = service.require_admin(
        workspace_id="ws_1",
        actor=actor,
        action="permission_scope.remove",
        target_type="github_repository",
        target_id="repo_1",
    )

    assert result.allowed is False
    assert result.reason == "missing_admin_role"
    record = audit_log.list_for_workspace("ws_1")[0]
    assert record.decision == "denied"
    assert record.reason == "missing_admin_role"
