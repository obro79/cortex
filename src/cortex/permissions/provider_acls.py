from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.contracts.entities import SourceChunk
from cortex.db.models import (
    ProviderAclEntryRecord,
    ProviderAclSnapshotRecord,
    ProviderPrincipalMappingRecord,
)
from cortex.ingestion.payloads import sha256_digest
from cortex.permissions.scopes import scope_external_id_hash


@dataclass(frozen=True)
class ProviderAclPrincipal:
    provider: str
    principal_type: str
    external_id_hash: str

    @classmethod
    def from_external_id(
        cls, *, provider: str, principal_type: str, external_id: str
    ) -> ProviderAclPrincipal:
        return cls(
            provider=provider,
            principal_type=principal_type,
            external_id_hash=provider_acl_id_hash(
                provider=provider,
                acl_type=principal_type,
                external_id=external_id,
            ),
        )


@dataclass(frozen=True)
class ProviderAclEntry:
    principal: ProviderAclPrincipal
    permission: str = "read"
    effect: str = "allow"


@dataclass(frozen=True)
class ProviderAclResourceRef:
    provider: str
    resource_type: str
    external_id_hash: str


@dataclass(frozen=True)
class ProviderAclSnapshot:
    id: str
    workspace_id: str
    resource: ProviderAclResourceRef
    entries: tuple[ProviderAclEntry, ...]
    snapshot_hash: str
    captured_at: datetime
    expires_at: datetime
    source_connection_id: str | None = None
    metadata_json: dict[str, object] | None = None


@dataclass(frozen=True)
class ProviderAclDecision:
    allowed: bool
    reason: str
    snapshot_id: str | None = None


class ProviderAclSnapshotIntegrityError(RuntimeError):
    """Raised when more than one authoritative ACL exists for a resource.

    Callers must fail closed rather than picking whichever row happened to be
    returned first, which could resurrect a revoked principal.
    """


@dataclass(frozen=True)
class ProviderPrincipalMapping:
    id: str
    workspace_id: str
    user_id: str
    principal: ProviderAclPrincipal
    match_method: str
    status: str
    last_verified_at: datetime
    expires_at: datetime
    metadata_json: dict[str, object] | None = None


def provider_acl_id_hash(*, provider: str, acl_type: str, external_id: str) -> str:
    normalized = f"{provider}:{acl_type}:{external_id}".lower()
    return sha256_digest(normalized.encode())


class InMemoryProviderAclRepository:
    def __init__(self) -> None:
        self._snapshots: dict[tuple[str, str, str, str], ProviderAclSnapshot] = {}

    def replace_snapshot(
        self,
        *,
        workspace_id: str,
        resource: ProviderAclResourceRef,
        entries: list[ProviderAclEntry],
        captured_at: datetime | None = None,
        expires_at: datetime | None = None,
        source_connection_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> ProviderAclSnapshot:
        captured = captured_at or datetime.now(UTC)
        expiry = expires_at or captured + timedelta(hours=24)
        snapshot_hash = _snapshot_hash(resource, entries)
        snapshot = ProviderAclSnapshot(
            id=f"pacl_{snapshot_hash.removeprefix('sha256:')[:24]}",
            workspace_id=workspace_id,
            resource=resource,
            entries=tuple(entries),
            snapshot_hash=snapshot_hash,
            captured_at=captured,
            expires_at=expiry,
            source_connection_id=source_connection_id,
            metadata_json=metadata_json or {},
        )
        self._snapshots[_snapshot_key(workspace_id, resource)] = snapshot
        return snapshot

    def current_snapshot(
        self, *, workspace_id: str, resource: ProviderAclResourceRef
    ) -> ProviderAclSnapshot | None:
        return self._snapshots.get(_snapshot_key(workspace_id, resource))

    def authorize(
        self,
        *,
        workspace_id: str,
        resource: ProviderAclResourceRef,
        principals: list[ProviderAclPrincipal],
        now: datetime | None = None,
    ) -> ProviderAclDecision:
        return _authorize_snapshot(
            snapshot=self.current_snapshot(
                workspace_id=workspace_id,
                resource=resource,
            ),
            principals=principals,
            now=now,
        )

    @classmethod
    def from_snapshots(
        cls, snapshots: list[ProviderAclSnapshot]
    ) -> InMemoryProviderAclRepository:
        """Create a read-only-in-practice authorization snapshot from SQL rows."""
        repository = cls()
        for snapshot in snapshots:
            key = _snapshot_key(snapshot.workspace_id, snapshot.resource)
            if key in repository._snapshots:
                raise ProviderAclSnapshotIntegrityError(
                    "duplicate_current_provider_acl_snapshot"
                )
            repository._snapshots[key] = snapshot
        return repository


class SqlAlchemyProviderAclRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_snapshot(
        self,
        *,
        workspace_id: str,
        resource: ProviderAclResourceRef,
        entries: list[ProviderAclEntry],
        captured_at: datetime | None = None,
        expires_at: datetime | None = None,
        source_connection_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> ProviderAclSnapshot:
        captured = captured_at or datetime.now(UTC)
        expiry = expires_at or captured + timedelta(hours=24)
        snapshot_hash = _snapshot_hash(resource, entries)
        snapshot_id = _sql_snapshot_id(snapshot_hash, captured)
        await self.session.execute(
            update(ProviderAclSnapshotRecord)
            .where(
                ProviderAclSnapshotRecord.workspace_id == workspace_id,
                ProviderAclSnapshotRecord.provider == resource.provider,
                ProviderAclSnapshotRecord.resource_type == resource.resource_type,
                ProviderAclSnapshotRecord.resource_id_hash == resource.external_id_hash,
                ProviderAclSnapshotRecord.is_current.is_(True),
            )
            .values(is_current=False)
        )
        snapshot_record = ProviderAclSnapshotRecord(
            id=snapshot_id,
            workspace_id=workspace_id,
            provider=resource.provider,
            resource_type=resource.resource_type,
            resource_id_hash=resource.external_id_hash,
            source_connection_id=source_connection_id,
            snapshot_hash=snapshot_hash,
            is_current=True,
            captured_at=captured,
            expires_at=expiry,
            metadata_json=metadata_json or {},
            created_at=captured,
        )
        self.session.add(snapshot_record)
        for index, entry in enumerate(entries):
            self.session.add(
                ProviderAclEntryRecord(
                    id=f"paclen_{snapshot_id.removeprefix('pacl_')[:20]}_{index}",
                    snapshot_id=snapshot_id,
                    workspace_id=workspace_id,
                    provider=resource.provider,
                    resource_type=resource.resource_type,
                    resource_id_hash=resource.external_id_hash,
                    principal_type=entry.principal.principal_type,
                    principal_id_hash=entry.principal.external_id_hash,
                    permission=entry.permission,
                    effect=entry.effect,
                    created_at=captured,
                )
            )
        await self.session.flush()
        return ProviderAclSnapshot(
            id=snapshot_id,
            workspace_id=workspace_id,
            resource=resource,
            entries=tuple(entries),
            snapshot_hash=snapshot_hash,
            captured_at=captured,
            expires_at=expiry,
            source_connection_id=source_connection_id,
            metadata_json=metadata_json or {},
        )

    async def current_snapshot(
        self, *, workspace_id: str, resource: ProviderAclResourceRef
    ) -> ProviderAclSnapshot | None:
        result = await self.session.execute(
            select(ProviderAclSnapshotRecord).where(
                ProviderAclSnapshotRecord.workspace_id == workspace_id,
                ProviderAclSnapshotRecord.provider == resource.provider,
                ProviderAclSnapshotRecord.resource_type == resource.resource_type,
                ProviderAclSnapshotRecord.resource_id_hash == resource.external_id_hash,
                ProviderAclSnapshotRecord.is_current.is_(True),
            )
        )
        records = list(result.scalars())
        if not records:
            return None
        if len(records) != 1:
            raise ProviderAclSnapshotIntegrityError(
                "duplicate_current_provider_acl_snapshot"
            )
        record = records[0]
        entries_result = await self.session.execute(
            select(ProviderAclEntryRecord).where(
                ProviderAclEntryRecord.snapshot_id == record.id
            )
        )
        return provider_acl_snapshot_from_records(
            record, list(entries_result.scalars())
        )

    async def list_current_snapshots(
        self, workspace_id: str
    ) -> list[ProviderAclSnapshot]:
        """Load all current ACL resources for one durable retrieval snapshot."""
        snapshots_result = await self.session.execute(
            select(ProviderAclSnapshotRecord).where(
                ProviderAclSnapshotRecord.workspace_id == workspace_id,
                ProviderAclSnapshotRecord.is_current.is_(True),
            )
        )
        records = list(snapshots_result.scalars())
        if not records:
            return []
        seen_resources: set[tuple[str, str, str, str]] = set()
        for record in records:
            key = (
                record.workspace_id,
                record.provider,
                record.resource_type,
                record.resource_id_hash,
            )
            if key in seen_resources:
                raise ProviderAclSnapshotIntegrityError(
                    "duplicate_current_provider_acl_snapshot"
                )
            seen_resources.add(key)
        entries_result = await self.session.execute(
            select(ProviderAclEntryRecord).where(
                ProviderAclEntryRecord.snapshot_id.in_(
                    [record.id for record in records]
                )
            )
        )
        entries_by_snapshot: dict[str, list[ProviderAclEntryRecord]] = {}
        for entry in entries_result.scalars():
            entries_by_snapshot.setdefault(entry.snapshot_id, []).append(entry)
        return [
            provider_acl_snapshot_from_records(
                record, entries_by_snapshot.get(record.id, [])
            )
            for record in records
        ]

    async def authorize(
        self,
        *,
        workspace_id: str,
        resource: ProviderAclResourceRef,
        principals: list[ProviderAclPrincipal],
        now: datetime | None = None,
    ) -> ProviderAclDecision:
        return _authorize_snapshot(
            snapshot=await self.current_snapshot(
                workspace_id=workspace_id,
                resource=resource,
            ),
            principals=principals,
            now=now,
        )


class InMemoryProviderPrincipalMappingRepository:
    def __init__(self) -> None:
        self._mappings: dict[str, ProviderPrincipalMapping] = {}

    def upsert_mapping(
        self,
        *,
        workspace_id: str,
        user_id: str,
        provider: str,
        principal_type: str,
        external_id: str,
        match_method: str,
        last_verified_at: datetime | None = None,
        expires_at: datetime | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> ProviderPrincipalMapping:
        verified_at = last_verified_at or datetime.now(UTC)
        principal = ProviderAclPrincipal.from_external_id(
            provider=provider,
            principal_type=principal_type,
            external_id=external_id,
        )
        mapping = ProviderPrincipalMapping(
            id=_principal_mapping_id(
                workspace_id=workspace_id,
                user_id=user_id,
                principal=principal,
            ),
            workspace_id=workspace_id,
            user_id=user_id,
            principal=principal,
            match_method=match_method,
            status="active",
            last_verified_at=verified_at,
            expires_at=expires_at or verified_at + timedelta(days=7),
            metadata_json=metadata_json or {},
        )
        self._mappings[mapping.id] = mapping
        return mapping

    def active_principals(
        self,
        *,
        workspace_id: str,
        user_id: str,
        now: datetime | None = None,
    ) -> list[ProviderAclPrincipal]:
        current = now or datetime.now(UTC)
        return [
            mapping.principal
            for mapping in self._mappings.values()
            if mapping.workspace_id == workspace_id
            and mapping.user_id == user_id
            and mapping.status == "active"
            and mapping.expires_at > current
        ]


class SqlAlchemyProviderPrincipalMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_mapping(
        self,
        *,
        workspace_id: str,
        user_id: str,
        provider: str,
        principal_type: str,
        external_id: str,
        match_method: str,
        last_verified_at: datetime | None = None,
        expires_at: datetime | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> ProviderPrincipalMapping:
        verified_at = last_verified_at or datetime.now(UTC)
        principal = ProviderAclPrincipal.from_external_id(
            provider=provider,
            principal_type=principal_type,
            external_id=external_id,
        )
        mapping_id = _principal_mapping_id(
            workspace_id=workspace_id,
            user_id=user_id,
            principal=principal,
        )
        record = await self.session.get(ProviderPrincipalMappingRecord, mapping_id)
        if record is None:
            record = ProviderPrincipalMappingRecord(
                id=mapping_id,
                workspace_id=workspace_id,
                user_id=user_id,
                provider=principal.provider,
                principal_type=principal.principal_type,
                principal_id_hash=principal.external_id_hash,
                match_method=match_method,
                status="active",
                last_verified_at=verified_at,
                expires_at=expires_at or verified_at + timedelta(days=7),
                metadata_json=metadata_json or {},
                created_at=verified_at,
                updated_at=verified_at,
            )
            self.session.add(record)
        else:
            record.match_method = match_method
            record.status = "active"
            record.last_verified_at = verified_at
            record.expires_at = expires_at or verified_at + timedelta(days=7)
            record.metadata_json = metadata_json or {}
            record.updated_at = verified_at
        await self.session.flush()
        return provider_principal_mapping_from_record(record)

    async def active_principals(
        self,
        *,
        workspace_id: str,
        user_id: str,
        now: datetime | None = None,
    ) -> list[ProviderAclPrincipal]:
        current = now or datetime.now(UTC)
        result = await self.session.execute(
            select(ProviderPrincipalMappingRecord).where(
                ProviderPrincipalMappingRecord.workspace_id == workspace_id,
                ProviderPrincipalMappingRecord.user_id == user_id,
                ProviderPrincipalMappingRecord.status == "active",
                ProviderPrincipalMappingRecord.expires_at > current,
            )
        )
        return [
            provider_principal_mapping_from_record(record).principal
            for record in result.scalars()
        ]


def provider_principal_mapping_from_record(
    record: ProviderPrincipalMappingRecord,
) -> ProviderPrincipalMapping:
    return ProviderPrincipalMapping(
        id=record.id,
        workspace_id=record.workspace_id,
        user_id=record.user_id,
        principal=ProviderAclPrincipal(
            provider=record.provider,
            principal_type=record.principal_type,
            external_id_hash=record.principal_id_hash,
        ),
        match_method=record.match_method,
        status=record.status,
        last_verified_at=record.last_verified_at,
        expires_at=record.expires_at,
        metadata_json=dict(record.metadata_json),
    )


def provider_acl_snapshot_from_records(
    record: ProviderAclSnapshotRecord,
    entry_records: list[ProviderAclEntryRecord],
) -> ProviderAclSnapshot:
    return ProviderAclSnapshot(
        id=record.id,
        workspace_id=record.workspace_id,
        resource=ProviderAclResourceRef(
            provider=record.provider,
            resource_type=record.resource_type,
            external_id_hash=record.resource_id_hash,
        ),
        entries=tuple(
            ProviderAclEntry(
                principal=ProviderAclPrincipal(
                    provider=entry.provider,
                    principal_type=entry.principal_type,
                    external_id_hash=entry.principal_id_hash,
                ),
                permission=entry.permission,
                effect=entry.effect,
            )
            for entry in entry_records
        ),
        snapshot_hash=record.snapshot_hash,
        captured_at=record.captured_at,
        expires_at=record.expires_at,
        source_connection_id=record.source_connection_id,
        metadata_json=dict(record.metadata_json),
    )


def provider_acl_resources_for_chunk(
    chunk: SourceChunk,
) -> list[ProviderAclResourceRef]:
    metadata = chunk.metadata_json
    provider = str(metadata.get("provider") or "")
    if not provider:
        provider = _provider_from_metadata(metadata)
    resources: list[ProviderAclResourceRef] = []
    if provider == "slack":
        channel_hash = metadata.get("channel_id_hash")
        if isinstance(channel_hash, str) and channel_hash:
            resources.append(
                ProviderAclResourceRef(
                    provider="slack",
                    resource_type="slack_channel",
                    external_id_hash=channel_hash,
                )
            )
    if provider == "github":
        repo_id = metadata.get("repo_id")
        if isinstance(repo_id, str) and repo_id:
            resources.append(
                ProviderAclResourceRef(
                    provider="github",
                    resource_type="github_repository",
                    external_id_hash=scope_external_id_hash(
                        "github", "github_repository", repo_id
                    ),
                )
            )
    if provider == "linear":
        team_id = metadata.get("team_id")
        project_id = metadata.get("project_id")
        if isinstance(team_id, str) and team_id:
            resources.append(
                ProviderAclResourceRef(
                    provider="linear",
                    resource_type="linear_team",
                    external_id_hash=scope_external_id_hash(
                        "linear", "linear_team", team_id
                    ),
                )
            )
        if isinstance(project_id, str) and project_id:
            resources.append(
                ProviderAclResourceRef(
                    provider="linear",
                    resource_type="linear_project",
                    external_id_hash=scope_external_id_hash(
                        "linear", "linear_project", project_id
                    ),
                )
            )
    return resources


def _authorize_snapshot(
    *,
    snapshot: ProviderAclSnapshot | None,
    principals: list[ProviderAclPrincipal],
    now: datetime | None = None,
) -> ProviderAclDecision:
    if snapshot is None:
        return ProviderAclDecision(False, "provider_acl_missing_snapshot")
    current = now or datetime.now(UTC)
    if snapshot.expires_at <= current:
        return ProviderAclDecision(
            False,
            "provider_acl_stale",
            snapshot_id=snapshot.id,
        )
    principal_keys = {
        (principal.provider, principal.principal_type, principal.external_id_hash)
        for principal in principals
    }
    for entry in snapshot.entries:
        if entry.effect != "allow" or entry.permission != "read":
            continue
        key = (
            entry.principal.provider,
            entry.principal.principal_type,
            entry.principal.external_id_hash,
        )
        if key in principal_keys:
            return ProviderAclDecision(
                True,
                "provider_acl",
                snapshot_id=snapshot.id,
            )
    return ProviderAclDecision(
        False,
        "provider_acl_denied",
        snapshot_id=snapshot.id,
    )


def _snapshot_hash(
    resource: ProviderAclResourceRef, entries: list[ProviderAclEntry]
) -> str:
    parts = [
        (
            f"{entry.principal.provider}:{entry.principal.principal_type}:"
            f"{entry.principal.external_id_hash}:{entry.permission}:{entry.effect}"
        )
        for entry in entries
    ]
    parts.append(
        f"{resource.provider}:{resource.resource_type}:{resource.external_id_hash}"
    )
    return sha256_digest("|".join(sorted(parts)).encode())


def _sql_snapshot_id(snapshot_hash: str, captured_at: datetime) -> str:
    digest = sha256_digest(f"{snapshot_hash}:{captured_at.isoformat()}".encode())
    return f"pacl_{digest.removeprefix('sha256:')[:24]}"


def _snapshot_key(
    workspace_id: str, resource: ProviderAclResourceRef
) -> tuple[str, str, str, str]:
    return (
        workspace_id,
        resource.provider,
        resource.resource_type,
        resource.external_id_hash,
    )


def _principal_mapping_id(
    *,
    workspace_id: str,
    user_id: str,
    principal: ProviderAclPrincipal,
) -> str:
    digest = sha256_digest(
        (
            f"{workspace_id}:{user_id}:{principal.provider}:"
            f"{principal.principal_type}:{principal.external_id_hash}"
        ).encode()
    )
    return f"ppm_{digest.removeprefix('sha256:')[:24]}"


def _provider_from_metadata(metadata: dict[str, object]) -> str:
    source_kind = str(metadata.get("source_kind", ""))
    object_type = str(metadata.get("object_type", ""))
    if source_kind.startswith("slack_"):
        return "slack"
    if source_kind.startswith("github_"):
        return "github"
    if source_kind.startswith("linear_"):
        return "linear"
    if object_type.startswith("github_"):
        return "github"
    if object_type.startswith("linear_"):
        return "linear"
    return ""
