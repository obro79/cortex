from datetime import UTC, datetime

import pytest

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.contracts.entities import SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.ingestion.payloads import sha256_digest
from cortex.permissions.provider_acls import (
    InMemoryProviderAclRepository,
    ProviderAclEntry,
    ProviderAclPrincipal,
    ProviderAclResourceRef,
    ProviderAclSnapshotIntegrityError,
)
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


def test_provider_acl_snapshot_allows_matching_native_principal() -> None:
    channel_id = "C123"
    chunk = SourceAwareChunker(
        load_retrieval_config().chunking
    ).chunks_for_source_object(_slack_source_object(channel_id))[0]
    scopes = InMemoryPermissionScopeRepository()
    scopes.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id=channel_id,
    )
    principal = ProviderAclPrincipal.from_external_id(
        provider="slack",
        principal_type="user",
        external_id="U123",
    )
    provider_acls = InMemoryProviderAclRepository()
    provider_acls.replace_snapshot(
        workspace_id="ws_1",
        resource=ProviderAclResourceRef(
            provider="slack",
            resource_type="slack_channel",
            external_id_hash=sha256_digest(channel_id.encode()),
        ),
        entries=[ProviderAclEntry(principal=principal)],
    )
    service = PermissionService(scopes, provider_acls=provider_acls)

    check = service.check_chunk(
        workspace_id="ws_1",
        chunk=chunk,
        caller_principals=[principal],
    )

    assert check.decision == "allowed"
    assert check.reason == "provider_acl"


def test_provider_acl_snapshot_fails_closed_when_missing() -> None:
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
    service = PermissionService(
        scopes,
        provider_acls=InMemoryProviderAclRepository(),
    )

    check = service.check_chunk(
        workspace_id="ws_1",
        chunk=chunk,
        caller_principals=[
            ProviderAclPrincipal.from_external_id(
                provider="slack",
                principal_type="user",
                external_id="U123",
            )
        ],
    )

    assert check.decision == "denied"
    assert check.reason == "provider_acl_missing_snapshot"


def test_provider_acl_snapshot_materialization_rejects_duplicates() -> None:
    repository = InMemoryProviderAclRepository()
    snapshot = repository.replace_snapshot(
        workspace_id="ws_1",
        resource=ProviderAclResourceRef(
            provider="slack",
            resource_type="slack_channel",
            external_id_hash=sha256_digest(b"C123"),
        ),
        entries=[],
    )

    with pytest.raises(
        ProviderAclSnapshotIntegrityError,
        match="duplicate_current_provider_acl_snapshot",
    ):
        InMemoryProviderAclRepository.from_snapshots([snapshot, snapshot])
