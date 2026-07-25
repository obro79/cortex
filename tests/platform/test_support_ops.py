from __future__ import annotations

from cortex.platform import SupportOpsService
from cortex.security.admin_auth import AdminActor, AdminAuthorizationService
from cortex.security.audit import InMemoryAuditLogRepository


def test_support_operation_allows_admin_and_audits_pointer_only_target() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = SupportOpsService(AdminAuthorizationService(audit_log))
    actor = AdminActor(
        actor_id="actor_1",
        workspace_id="ws_1",
        roles=frozenset({"workspace_admin"}),
    )

    result = service.force_reembed(
        workspace_id="ws_1", actor=actor, source_chunk_id="chunk_private_1"
    )

    assert result.ok is True
    assert result.status == "accepted"
    record = audit_log.list_for_workspace("ws_1")[0]
    assert record.action == "support_ops.force_reembed"
    assert record.target_id_hash is not None
    assert record.target_id_hash != "chunk_private_1"
    assert "chunk_private_1" not in str(record.metadata_json)


def test_support_operation_denies_member_and_audits_attempt() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = SupportOpsService(AdminAuthorizationService(audit_log))
    actor = AdminActor(
        actor_id="actor_2",
        workspace_id="ws_1",
        roles=frozenset({"member"}),
    )

    result = service.deadletter_replay(
        workspace_id="ws_1", actor=actor, raw_event_id="raw_1"
    )

    assert result.ok is False
    assert result.status == "denied"
    assert result.reason == "missing_admin_role"
    record = audit_log.list_for_workspace("ws_1")[0]
    assert record.decision == "denied"
    assert record.reason == "missing_admin_role"


def test_support_ops_cover_phase_13_operation_set() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = SupportOpsService(AdminAuthorizationService(audit_log))
    actor = AdminActor(
        actor_id="actor_1",
        workspace_id="ws_1",
        roles=frozenset({"security_admin"}),
    )

    results = [
        service.connector_resync(
            workspace_id="ws_1", actor=actor, source_connection_id="src_1"
        ),
        service.deadletter_replay(
            workspace_id="ws_1", actor=actor, raw_event_id="raw_1"
        ),
        service.force_reembed(
            workspace_id="ws_1", actor=actor, source_chunk_id="chunk_1"
        ),
        service.force_reindex(
            workspace_id="ws_1", actor=actor, source_object_id="obj_1"
        ),
        service.inspect_source_health(
            workspace_id="ws_1", actor=actor, source_connection_id="src_1"
        ),
    ]

    assert [result.operation for result in results] == [
        "connector_resync",
        "deadletter_replay",
        "force_reembed",
        "force_reindex",
        "source_health_inspect",
    ]
    assert all(result.ok for result in results)
    assert len(audit_log.list_for_workspace("ws_1")) == 5
