from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from cryptography.fernet import Fernet

from cortex.config import Settings
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.db.models import PermissionScopeRecord
from cortex.permissions.scopes import (
    SqlAlchemyPermissionScopeRepository,
    SqlAlchemyPermissionScopeService,
    load_permission_service_snapshot,
    scope_external_id_hash,
)


class _ScalarResult:
    def __init__(self, records: list[PermissionScopeRecord]) -> None:
        self._records = records

    def scalars(self) -> _ScalarResult:
        return self

    def __iter__(self):
        return iter(self._records)


class _ScopeSession:
    """Minimal persistent async-session double for repository contract tests."""

    def __init__(self) -> None:
        self.records: dict[str, PermissionScopeRecord] = {}

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

    async def execute(self, _statement: Any) -> _ScalarResult:
        active = [
            record for record in self.records.values() if record.status == "active"
        ]
        return _ScalarResult(sorted(active, key=lambda record: record.id))


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
