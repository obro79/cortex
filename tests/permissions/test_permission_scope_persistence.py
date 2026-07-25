from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from cryptography.fernet import Fernet

from cortex.config import Settings
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.contracts.entities import SourceChunk
from cortex.contracts.enums import SourceChunkStatus
from cortex.db.models import (
    PermissionScopeRecord,
    ProviderAclEntryRecord,
    ProviderAclSnapshotRecord,
)
from cortex.ingestion.payloads import sha256_digest
from cortex.permissions.provider_acls import (
    ProviderAclPrincipal,
    ProviderAclSnapshotIntegrityError,
)
from cortex.permissions.scopes import (
    SqlAlchemyPermissionScopeRepository,
    SqlAlchemyPermissionScopeService,
    load_permission_service_snapshot,
    scope_external_id_hash,
)


class _ScalarResult:
    def __init__(self, records: list[Any]) -> None:
        self._records = records

    def scalars(self) -> _ScalarResult:
        return self

    def __iter__(self):
        return iter(self._records)

    def scalar_one_or_none(self) -> Any | None:
        return self._records[0] if self._records else None


class _ScopeSession:
    """Minimal persistent async-session double for repository contract tests."""

    def __init__(self) -> None:
        self.records: dict[str, PermissionScopeRecord] = {}
        self.acl_snapshots: dict[str, ProviderAclSnapshotRecord] = {}
        self.acl_entries: dict[str, ProviderAclEntryRecord] = {}

    async def get(
        self, _model: type[PermissionScopeRecord], record_id: str
    ) -> PermissionScopeRecord | None:
        return self.records.get(record_id)

    def add(self, record: PermissionScopeRecord) -> None:
        self.records[record.id] = record

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    @asynccontextmanager
    async def begin_nested(self) -> AsyncIterator[None]:
        yield

    async def execute(self, statement: Any) -> _ScalarResult:
        entity = statement.column_descriptions[0]["entity"]
        if entity is PermissionScopeRecord:
            active = [
                record for record in self.records.values() if record.status == "active"
            ]
            return _ScalarResult(sorted(active, key=lambda record: record.id))
        if entity is ProviderAclSnapshotRecord:
            return _ScalarResult(
                [record for record in self.acl_snapshots.values() if record.is_current]
            )
        if entity is ProviderAclEntryRecord:
            return _ScalarResult(list(self.acl_entries.values()))
        raise AssertionError(f"unexpected query entity: {entity}")


class _ScopeSessionFactory:
    def __init__(self, session: _ScopeSession) -> None:
        self.session = session

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[_ScopeSession]:
        yield self.session


async def test_sql_scope_repository_persists_only_hashes_and_survives_rebuild() -> None:
    session = _ScopeSession()
    first = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]

    scope = await first.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C_PRIVATE_123",
        metadata_json={"purpose": "demo"},
        actor_id="user_1",
    )

    stored = session.records[scope.id]
    assert stored.external_id_hash == scope_external_id_hash(
        "slack", "slack_channel", "C_PRIVATE_123"
    )
    assert "C_PRIVATE_123" not in str(stored.__dict__)

    restarted = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]
    active = await restarted.list_active("ws_1")
    assert [record.id for record in active] == [scope.id]
    assert active[0].created_by_actor_id == "user_1"


async def test_sql_snapshot_fails_closed_after_scope_removal() -> None:
    session = _ScopeSession()
    repository = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]
    await repository.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )
    before_removal = await load_permission_service_snapshot(session, "ws_1")  # type: ignore[arg-type]
    assert before_removal.scopes.list_active("ws_1")

    removed = await repository.remove(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
        actor_id="user_2",
    )
    assert removed is not None
    assert removed.removed_at is not None
    assert removed.removed_at <= datetime.now(UTC)
    assert removed.removed_by_actor_id == "user_2"

    after_removal = await load_permission_service_snapshot(session, "ws_1")  # type: ignore[arg-type]
    assert after_removal.scopes.list_active("ws_1") == []


async def test_sql_scope_remove_cannot_cross_workspace() -> None:
    session = _ScopeSession()
    repository = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]
    await repository.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )

    removed = await repository.remove(
        workspace_id="ws_2",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )

    assert removed is None
    assert len(await repository.list_active("ws_1")) == 1


async def test_sql_scope_service_survives_connector_service_rebuild() -> None:
    session = _ScopeSession()
    session_factory = _ScopeSessionFactory(session)
    first = SqlAlchemyPermissionScopeService(session_factory)  # type: ignore[arg-type]
    await first.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )

    restarted = SqlAlchemyPermissionScopeService(session_factory)  # type: ignore[arg-type]
    assert len(await restarted.list_active("ws_1")) == 1


def test_sql_slack_factory_uses_session_factory_scope_service() -> None:
    services = create_slack_connector_services(
        settings=Settings(
            cortex_state_backend="sql",
            cortex_secret_encryption_key=Fernet.generate_key().decode(),
        ),
        session_factory=_ScopeSessionFactory(_ScopeSession()),  # type: ignore[arg-type]
    )

    assert isinstance(
        services.permission_scope_repository, SqlAlchemyPermissionScopeService
    )


def _slack_chunk(channel_id: str = "C123") -> SourceChunk:
    now = datetime.now(UTC)
    return SourceChunk(
        id="chunk_1",
        workspace_id="ws_1",
        source_object_id="source_1",
        chunk_type="slack_thread",
        chunk_index=0,
        text="private roadmap",
        text_hash="sha256:chunk",
        chunking_version="v1",
        metadata_json={
            "source_kind": "slack_message",
            "channel_id_hash": sha256_digest(channel_id.encode()),
        },
        status=SourceChunkStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


async def test_sql_permission_snapshot_enforces_materialized_provider_acl() -> None:
    session = _ScopeSession()
    repository = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]
    await repository.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )
    now = datetime.now(UTC)
    channel_hash = sha256_digest(b"C123")
    principal = ProviderAclPrincipal.from_external_id(
        provider="slack", principal_type="user", external_id="U123"
    )
    session.acl_snapshots["acl_1"] = ProviderAclSnapshotRecord(
        id="acl_1",
        workspace_id="ws_1",
        provider="slack",
        resource_type="slack_channel",
        resource_id_hash=channel_hash,
        snapshot_hash="sha256:acl",
        is_current=True,
        captured_at=now,
        expires_at=now.replace(year=now.year + 1),
        metadata_json={},
        created_at=now,
    )
    session.acl_entries["acl_entry_1"] = ProviderAclEntryRecord(
        id="acl_entry_1",
        snapshot_id="acl_1",
        workspace_id="ws_1",
        provider="slack",
        resource_type="slack_channel",
        resource_id_hash=channel_hash,
        principal_type="user",
        principal_id_hash=principal.external_id_hash,
        permission="read",
        effect="allow",
        created_at=now,
    )

    service = await load_permission_service_snapshot(session, "ws_1")  # type: ignore[arg-type]
    allowed = service.check_chunk(
        workspace_id="ws_1",
        chunk=_slack_chunk(),
        caller_principals=[principal],
    )
    assert allowed.decision == "allowed"
    assert allowed.reason == "provider_acl"


async def test_sql_permission_snapshot_preserves_scope_without_acl_policy() -> None:
    session = _ScopeSession()
    repository = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]
    await repository.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )

    service = await load_permission_service_snapshot(session, "ws_1")  # type: ignore[arg-type]
    allowed = service.check_chunk(
        workspace_id="ws_1",
        chunk=_slack_chunk(),
    )
    assert allowed.decision == "allowed"
    assert allowed.reason == "permission_scope"


async def test_sql_permission_snapshot_denies_missing_resource_after_acl_policy() -> (
    None
):
    session = _ScopeSession()
    repository = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]
    await repository.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )
    now = datetime.now(UTC)
    session.acl_snapshots["acl_other"] = ProviderAclSnapshotRecord(
        id="acl_other",
        workspace_id="ws_1",
        provider="slack",
        resource_type="slack_channel",
        resource_id_hash=sha256_digest(b"C999"),
        snapshot_hash="sha256:other",
        is_current=True,
        captured_at=now,
        expires_at=now.replace(year=now.year + 1),
        metadata_json={},
        created_at=now,
    )

    service = await load_permission_service_snapshot(session, "ws_1")  # type: ignore[arg-type]
    principal = ProviderAclPrincipal.from_external_id(
        provider="slack", principal_type="user", external_id="U123"
    )
    denied = service.check_chunk(
        workspace_id="ws_1",
        chunk=_slack_chunk(),
        caller_principals=[principal],
    )
    assert denied.decision == "denied"
    assert denied.reason == "provider_acl_missing_snapshot"


async def test_sql_permission_snapshot_denies_stale_provider_acl() -> None:
    session = _ScopeSession()
    repository = SqlAlchemyPermissionScopeRepository(session)  # type: ignore[arg-type]
    await repository.upsert_active(
        workspace_id="ws_1",
        provider="slack",
        scope_type="slack_channel",
        external_id="C123",
    )
    now = datetime.now(UTC)
    session.acl_snapshots["acl_stale"] = ProviderAclSnapshotRecord(
        id="acl_stale",
        workspace_id="ws_1",
        provider="slack",
        resource_type="slack_channel",
        resource_id_hash=sha256_digest(b"C123"),
        snapshot_hash="sha256:stale",
        is_current=True,
        captured_at=now.replace(year=now.year - 1),
        expires_at=now.replace(year=now.year - 1),
        metadata_json={},
        created_at=now,
    )

    service = await load_permission_service_snapshot(session, "ws_1")  # type: ignore[arg-type]
    principal = ProviderAclPrincipal.from_external_id(
        provider="slack", principal_type="user", external_id="U123"
    )
    denied = service.check_chunk(
        workspace_id="ws_1",
        chunk=_slack_chunk(),
        caller_principals=[principal],
    )
    assert denied.decision == "denied"
    assert denied.reason == "provider_acl_stale"


async def test_sql_permission_snapshot_rejects_duplicate_current_acl_resources() -> (
    None
):
    session = _ScopeSession()
    now = datetime.now(UTC)
    resource_hash = sha256_digest(b"C123")
    for record_id in ("acl_a", "acl_b"):
        session.acl_snapshots[record_id] = ProviderAclSnapshotRecord(
            id=record_id,
            workspace_id="ws_1",
            provider="slack",
            resource_type="slack_channel",
            resource_id_hash=resource_hash,
            snapshot_hash=f"sha256:{record_id}",
            is_current=True,
            captured_at=now,
            expires_at=now.replace(year=now.year + 1),
            metadata_json={},
            created_at=now,
        )

    with pytest.raises(
        ProviderAclSnapshotIntegrityError,
        match="duplicate_current_provider_acl_snapshot",
    ):
        await load_permission_service_snapshot(session, "ws_1")  # type: ignore[arg-type]
