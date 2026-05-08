from __future__ import annotations

from datetime import UTC, datetime

from cortex.contracts.entities import PermissionScope, PermissionSnapshot
from cortex.contracts.enums import PermissionScopeStatus
from cortex.ingestion.payloads import sha256_digest


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
