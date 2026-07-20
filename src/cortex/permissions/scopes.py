from __future__ import annotations

from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.contracts.entities import PermissionScope, PermissionSnapshot
from cortex.contracts.enums import PermissionScopeStatus
from cortex.db.models import PermissionScopeRecord
from cortex.ingestion.payloads import sha256_digest

if TYPE_CHECKING:
    from cortex.permissions.service import PermissionService


def scope_external_id_hash(provider: str, scope_type: str, external_id: str) -> str:
    if provider == "slack" and scope_type == "slack_channel":
        return sha256_digest(external_id.encode())
    normalized = f"{provider}:{scope_type}:{external_id}".lower()
    return sha256_digest(normalized.encode())


def stable_scope_id(
    workspace_id: str, provider: str, scope_type: str, external_id_hash: str
) -> str:
    digest = sha256_digest(
        f"{workspace_id}:{provider}:{scope_type}:{external_id_hash}".encode()
    ).removeprefix("sha256:")
    return f"pscope_{digest[:24]}"


class InMemoryPermissionScopeRepository:
    def __init__(self) -> None:
        self._records: dict[str, PermissionScope] = {}

    def upsert_active(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        metadata_json: dict[str, object] | None = None,
        actor_id: str | None = None,
    ) -> PermissionScope:
        external_hash = scope_external_id_hash(provider, scope_type, external_id)
        now = datetime.now(UTC)
        record_id = stable_scope_id(workspace_id, provider, scope_type, external_hash)
        existing = self._records.get(record_id)
        update = {
            "status": PermissionScopeStatus.ACTIVE,
            "metadata_json": metadata_json or {},
            "created_by_actor_id": existing.created_by_actor_id
            if existing
            else actor_id,
            "removed_by_actor_id": None,
            "removed_at": None,
            "updated_at": now,
        }
        if existing is not None:
            updated = existing.model_copy(update=update)
            self._records[record_id] = updated
            return updated
        record = PermissionScope(
            id=record_id,
            workspace_id=workspace_id,
            provider=provider,
            scope_type=scope_type,
            external_id_hash=external_hash,
            status=PermissionScopeStatus.ACTIVE,
            metadata_json=metadata_json or {},
            created_by_actor_id=actor_id,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        return record

    def remove(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        actor_id: str | None = None,
    ) -> PermissionScope | None:
        external_hash = scope_external_id_hash(provider, scope_type, external_id)
        record_id = stable_scope_id(workspace_id, provider, scope_type, external_hash)
        record = self._records.get(record_id)
        if record is None:
            return None
        now = datetime.now(UTC)
        removed = record.model_copy(
            update={
                "status": PermissionScopeStatus.REMOVED,
                "removed_by_actor_id": actor_id,
                "removed_at": now,
                "updated_at": now,
            }
        )
        self._records[record_id] = removed
        return removed

    def list_active(self, workspace_id: str) -> list[PermissionScope]:
        return [
            record
            for record in self._records.values()
            if record.workspace_id == workspace_id
            and record.status == PermissionScopeStatus.ACTIVE
        ]

    def create_snapshot(self, workspace_id: str) -> PermissionSnapshot:
        active = self.list_active(workspace_id)
        parts = sorted(
            f"{scope.provider}:{scope.scope_type}:{scope.external_id_hash}"
            for scope in active
        )
        provider_counts: dict[str, int] = {}
        for scope in active:
            provider_counts[scope.provider] = provider_counts.get(scope.provider, 0) + 1
        now = datetime.now(UTC)
        snapshot_hash = sha256_digest("|".join(parts).encode())
        return PermissionSnapshot(
            id=f"psnap_{snapshot_hash.removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            snapshot_hash=snapshot_hash,
            scope_count=len(active),
            provider_counts_json=provider_counts,
            created_at=now,
        )

    @classmethod
    def from_active_scopes(
        cls, scopes: list[PermissionScope]
    ) -> InMemoryPermissionScopeRepository:
        """Create an isolated, fail-closed retrieval snapshot from durable scopes."""
        repository = cls()
        repository._records = {scope.id: scope for scope in scopes}
        return repository


class PermissionScopeRepository(Protocol):
    """Async durable scope contract used by connector and runtime composition."""

    def upsert_active(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        metadata_json: dict[str, object] | None = None,
        actor_id: str | None = None,
    ) -> Awaitable[PermissionScope]: ...

    def remove(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        actor_id: str | None = None,
    ) -> Awaitable[PermissionScope | None]: ...

    def list_active(self, workspace_id: str) -> Awaitable[list[PermissionScope]]: ...


class SqlAlchemyPermissionScopeRepository:
    """Permission scopes backed by one caller-owned SQLAlchemy transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_active(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        metadata_json: dict[str, object] | None = None,
        actor_id: str | None = None,
    ) -> PermissionScope:
        external_hash = scope_external_id_hash(provider, scope_type, external_id)
        record_id = stable_scope_id(workspace_id, provider, scope_type, external_hash)
        now = datetime.now(UTC)
        values = {
            "status": PermissionScopeStatus.ACTIVE.value,
            "metadata_json": metadata_json or {},
            "removed_by_actor_id": None,
            "removed_at": None,
            "updated_at": now,
        }
        record = await self.session.get(PermissionScopeRecord, record_id)
        if record is not None:
            for field, value in values.items():
                setattr(record, field, value)
            await self.session.flush()
            return permission_scope_from_record(record)

        # The deterministic ID and database uniqueness constraint make concurrent
        # selection idempotent. A nested savepoint keeps the caller transaction
        # usable when another writer wins the initial insert race.
        try:
            async with self.session.begin_nested():
                record = PermissionScopeRecord(
                    id=record_id,
                    workspace_id=workspace_id,
                    provider=provider,
                    scope_type=scope_type,
                    external_id_hash=external_hash,
                    created_by_actor_id=actor_id,
                    created_at=now,
                    **values,
                )
                self.session.add(record)
                await self.session.flush()
        except IntegrityError:
            record = await self.session.get(PermissionScopeRecord, record_id)
            if record is None:
                raise
            for field, value in values.items():
                setattr(record, field, value)
            await self.session.flush()
        assert record is not None
        return permission_scope_from_record(record)

    async def remove(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        actor_id: str | None = None,
    ) -> PermissionScope | None:
        external_hash = scope_external_id_hash(provider, scope_type, external_id)
        record_id = stable_scope_id(workspace_id, provider, scope_type, external_hash)
        record = await self.session.get(PermissionScopeRecord, record_id)
        if record is None or record.workspace_id != workspace_id:
            return None
        now = datetime.now(UTC)
        record.status = PermissionScopeStatus.REMOVED.value
        record.removed_by_actor_id = actor_id
        record.removed_at = now
        record.updated_at = now
        await self.session.flush()
        return permission_scope_from_record(record)

    async def list_active(self, workspace_id: str) -> list[PermissionScope]:
        result = await self.session.execute(
            select(PermissionScopeRecord)
            .where(
                PermissionScopeRecord.workspace_id == workspace_id,
                PermissionScopeRecord.status == PermissionScopeStatus.ACTIVE.value,
            )
            .order_by(PermissionScopeRecord.id)
        )
        return [permission_scope_from_record(record) for record in result.scalars()]

    async def materialize_permission_service(
        self, workspace_id: str
    ) -> PermissionService:
        """Load only active SQL scopes into an immutable-in-practice local snapshot.

        The returned service intentionally has no database handle; callers must
        materialize a new snapshot for each authorization request/batch.
        """
        from cortex.permissions.provider_acls import (
            InMemoryProviderAclRepository,
            SqlAlchemyProviderAclRepository,
        )
        from cortex.permissions.service import PermissionService

        snapshot = InMemoryPermissionScopeRepository.from_active_scopes(
            await self.list_active(workspace_id)
        )
        acl_snapshot = InMemoryProviderAclRepository.from_snapshots(
            await SqlAlchemyProviderAclRepository(self.session).list_current_snapshots(
                workspace_id
            )
        )
        return PermissionService(snapshot, provider_acls=acl_snapshot)


class SqlAlchemyPermissionScopeService:
    """Session-factory adapter for connector operations outside request scopes.

    Connector selection operations need durable scope changes but must not retain
    an application-wide ``AsyncSession``. This adapter owns one short
    transaction per operation; retrieval instead uses the repository/helper with
    its request-scoped session.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def upsert_active(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        metadata_json: dict[str, object] | None = None,
        actor_id: str | None = None,
    ) -> PermissionScope:
        async with self.session_factory() as session:
            scope = await SqlAlchemyPermissionScopeRepository(session).upsert_active(
                workspace_id=workspace_id,
                provider=provider,
                scope_type=scope_type,
                external_id=external_id,
                metadata_json=metadata_json,
                actor_id=actor_id,
            )
            await session.commit()
            return scope

    async def remove(
        self,
        *,
        workspace_id: str,
        provider: str,
        scope_type: str,
        external_id: str,
        actor_id: str | None = None,
    ) -> PermissionScope | None:
        async with self.session_factory() as session:
            scope = await SqlAlchemyPermissionScopeRepository(session).remove(
                workspace_id=workspace_id,
                provider=provider,
                scope_type=scope_type,
                external_id=external_id,
                actor_id=actor_id,
            )
            await session.commit()
            return scope

    async def list_active(self, workspace_id: str) -> list[PermissionScope]:
        async with self.session_factory() as session:
            return await SqlAlchemyPermissionScopeRepository(session).list_active(
                workspace_id
            )


def permission_scope_from_record(record: PermissionScopeRecord) -> PermissionScope:
    return PermissionScope(
        id=record.id,
        workspace_id=record.workspace_id,
        provider=record.provider,
        scope_type=record.scope_type,
        external_id_hash=record.external_id_hash,
        status=PermissionScopeStatus(record.status),
        metadata_json=dict(record.metadata_json),
        created_by_actor_id=record.created_by_actor_id,
        removed_by_actor_id=record.removed_by_actor_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        removed_at=record.removed_at,
    )


async def load_permission_service_snapshot(
    session: AsyncSession, workspace_id: str
) -> PermissionService:
    """Materialize active SQL scopes for one synchronous retrieval operation.

    This deliberately creates a fresh in-memory snapshot instead of exposing a
    long-lived mutable SQL repository to ``PermissionService``. An empty result
    therefore retains the existing deny-by-default retrieval behavior.
    """
    return await SqlAlchemyPermissionScopeRepository(
        session
    ).materialize_permission_service(workspace_id)
