from datetime import UTC, datetime

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.permissions.scopes import InMemoryPermissionScopeRepository
from cortex.permissions.service import PermissionService


def _slack_source_object(channel_id: str = "C123") -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id="so_slack",
        workspace_id="ws_1",
        source_connection_id="src_slack",
        provider="slack",
        object_type="slack_thread",
        external_object_id=f"T1:{channel_id}:1715000000.000100:1715000000.000100",
        external_object_key=f"slack:T1:{channel_id}:1715000000.000100:1715000000.000100",
        title="Slack thread",
        content_hash="sha256:slack-content",
        content_text="deploy notes mention COR-123",
        metadata_json={
            "source_kind": "slack_message",
            "channel_id_hash": sha256_digest(channel_id.encode()),
            "message_ts": "1715000000.000100",
            "thread_ts": "1715000000.000100",
            "has_files": False,
            "has_links": False,
        },
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_permission_service_fails_closed_without_active_scopes() -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(_slack_source_object())[0]
    service = PermissionService(InMemoryPermissionScopeRepository())

    check = service.check_chunk(workspace_id="ws_1", chunk=chunk)

    assert check.decision == "denied"
    assert check.reason == "no_active_permission_scope"


def test_permission_service_allows_selected_slack_channel() -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(_slack_source_object())[0]
    scopes = InMemoryPermissionScopeRepository()
    scopes.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )
    service = PermissionService(scopes)

    check = service.check_chunk(workspace_id="ws_1", chunk=chunk)

    assert check.decision == "allowed"
    assert check.reason == "permission_scope"


def test_removed_permission_scope_immediately_denies_retrieval() -> None:
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(_slack_source_object())[0]
    scopes = InMemoryPermissionScopeRepository()
    scopes.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )
    service = PermissionService(scopes)

    scopes.remove(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )

    check = service.check_chunk(workspace_id="ws_1", chunk=chunk)
    assert check.decision == "denied"
    assert check.reason == "no_active_permission_scope"
