from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.contracts.entities import SourceFile, SourceObject
from cortex.contracts.enums import SourceObjectStatus
from cortex.db.models import (
    RelationshipSeedRecord,
    SourceFileRecord,
    SourceObjectRecord,
)

from .result import RelationshipSeed


class NormalizationRepositoryError(Exception):
    pass


class SourceRecordNotFoundError(NormalizationRepositoryError):
    pass


class SourceLifecycleError(NormalizationRepositoryError):
    pass


@dataclass(frozen=True)
class UpsertResult[T]:
    record: T
    operation: str


TSource = TypeVar("TSource", SourceObject, SourceFile)


class InMemorySourceObjectRepository:
    def __init__(self) -> None:
        self._records: dict[str, SourceObject] = {}
        self._by_external_identity: dict[tuple[str, str, str, str], str] = {}

    def upsert_many(
        self, records: list[SourceObject]
    ) -> list[UpsertResult[SourceObject]]:
        return [self._upsert(record) for record in records]

    def get_by_id(self, source_object_id: str) -> SourceObject:
        try:
            return self._records[source_object_id]
        except KeyError as error:
            raise SourceRecordNotFoundError(source_object_id) from error

    def get_by_external_identity(
        self,
        workspace_id: str,
        provider: str,
        object_type: str,
        external_object_id: str,
    ) -> SourceObject | None:
        key = (workspace_id, provider, object_type, external_object_id)
        record_id = self._by_external_identity.get(key)
        return self._records[record_id] if record_id else None

    def mark_stale(self, source_object_id: str) -> SourceObject:
        record = self.get_by_id(source_object_id)
        return self._transition(record, SourceObjectStatus.STALE)

    def mark_deleted(self, source_object_id: str) -> SourceObject:
        record = self.get_by_id(source_object_id)
        return self._transition(
            record,
            SourceObjectStatus.DELETED,
            deleted_at=datetime.now(UTC),
        )

    def _upsert(self, record: SourceObject) -> UpsertResult[SourceObject]:
        existing = self.get_by_external_identity(
            record.workspace_id,
            record.provider,
            record.object_type,
            record.external_object_id,
        )
        if existing is None:
            self._records[record.id] = record
            self._by_external_identity[
                (
                    record.workspace_id,
                    record.provider,
                    record.object_type,
                    record.external_object_id,
                )
            ] = record.id
            return UpsertResult(record=record, operation="inserted")
        if (
            existing.content_hash == record.content_hash
            and existing.normalized_version == record.normalized_version
        ):
            return UpsertResult(record=existing, operation="noop")
        updated = record.model_copy(
            update={"id": existing.id, "created_at": existing.created_at}
        )
        self._records[existing.id] = updated
        return UpsertResult(record=updated, operation="updated")

    def _transition(
        self,
        record: SourceObject,
        status: SourceObjectStatus,
        **updates: object,
    ) -> SourceObject:
        current = SourceObjectStatus(record.status)
        if current == SourceObjectStatus.DELETED:
            raise SourceLifecycleError("deleted source objects are terminal")
        if status == SourceObjectStatus.ACTIVE and current != SourceObjectStatus.STALE:
            raise SourceLifecycleError(f"invalid transition: {current} -> {status}")
        updated = record.model_copy(
            update={"status": status, "updated_at": datetime.now(UTC), **updates}
        )
        self._records[record.id] = updated
        return updated


class InMemorySourceFileRepository:
    def __init__(self) -> None:
        self._records: dict[str, SourceFile] = {}
        self._by_external_file: dict[tuple[str, str, str], str] = {}

    def upsert_many(self, records: list[SourceFile]) -> list[UpsertResult[SourceFile]]:
        return [self._upsert(record) for record in records]

    def get_by_id(self, source_file_id: str) -> SourceFile:
        try:
            return self._records[source_file_id]
        except KeyError as error:
            raise SourceRecordNotFoundError(source_file_id) from error

    def get_by_external_file_id(
        self, workspace_id: str, provider: str, external_file_id: str
    ) -> SourceFile | None:
        key = (workspace_id, provider, external_file_id)
        record_id = self._by_external_file.get(key)
        return self._records[record_id] if record_id else None

    def mark_stale(self, source_file_id: str) -> SourceFile:
        return self._transition(
            self.get_by_id(source_file_id), SourceObjectStatus.STALE
        )

    def mark_deleted(self, source_file_id: str) -> SourceFile:
        return self._transition(
            self.get_by_id(source_file_id),
            SourceObjectStatus.DELETED,
            deleted_at=datetime.now(UTC),
        )

    def _upsert(self, record: SourceFile) -> UpsertResult[SourceFile]:
        if record.provider is None or record.external_file_id is None:
            raise NormalizationRepositoryError(
                "source files require provider and external_file_id"
            )
        existing = self.get_by_external_file_id(
            record.workspace_id, record.provider, record.external_file_id
        )
        if existing is None:
            self._records[record.id] = record
            self._by_external_file[
                (record.workspace_id, record.provider, record.external_file_id)
            ] = record.id
            return UpsertResult(record=record, operation="inserted")
        if (
            existing.content_hash == record.content_hash
            and existing.ocr_text_hash == record.ocr_text_hash
        ):
            return UpsertResult(record=existing, operation="noop")
        updated = record.model_copy(
            update={"id": existing.id, "created_at": existing.created_at}
        )
        self._records[existing.id] = updated
        return UpsertResult(record=updated, operation="updated")

    def _transition(
        self,
        record: SourceFile,
        status: SourceObjectStatus,
        **updates: object,
    ) -> SourceFile:
        current = SourceObjectStatus(record.status)
        if current == SourceObjectStatus.DELETED:
            raise SourceLifecycleError("deleted source files are terminal")
        updated = record.model_copy(
            update={"status": status, "updated_at": datetime.now(UTC), **updates}
        )
        self._records[record.id] = updated
        return updated


class InMemoryRelationshipSeedRepository:
    def __init__(self) -> None:
        self._records: dict[str, RelationshipSeed] = {}

    def upsert_many(
        self, records: list[RelationshipSeed]
    ) -> list[UpsertResult[RelationshipSeed]]:
        results: list[UpsertResult[RelationshipSeed]] = []
        for record in records:
            existing = self._records.get(record.id)
            if existing == record:
                results.append(UpsertResult(record=existing, operation="noop"))
            else:
                self._records[record.id] = record
                results.append(
                    UpsertResult(
                        record=record,
                        operation="inserted" if existing is None else "updated",
                    )
                )
        return results

    def list_all(self) -> list[RelationshipSeed]:
        return list(self._records.values())


def source_object_from_record(record: SourceObjectRecord) -> SourceObject:
    return SourceObject(
        id=record.id,
        workspace_id=record.workspace_id,
        source_connection_id=record.source_connection_id,
        provider=record.provider,
        object_type=record.object_type,
        external_object_id=record.external_object_id,
        external_object_key=record.external_object_key,
        parent_object_id=record.parent_object_id,
        title=record.title,
        canonical_url=record.canonical_url,
        author_external_id=record.author_external_id,
        occurred_at=record.occurred_at,
        source_updated_at=record.source_updated_at,
        normalized_version=record.normalized_version,
        content_hash=record.content_hash,
        content_text=record.content_text,
        metadata_json=record.metadata_json,
        status=SourceObjectStatus(record.status),
        superseded_by_id=record.superseded_by_id,
        deleted_at=record.deleted_at,
        trace_id=record.trace_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def source_file_from_record(record: SourceFileRecord) -> SourceFile:
    return SourceFile(
        id=record.id,
        workspace_id=record.workspace_id,
        source_object_id=record.source_object_id,
        source_connection_id=record.source_connection_id,
        provider=record.provider,
        external_file_id=record.external_file_id,
        external_object_key=record.external_object_key,
        file_name_hash=record.file_name_hash,
        content_type=record.content_type,
        storage_ref=record.storage_ref,
        content_hash=record.content_hash,
        ocr_text=record.ocr_text,
        ocr_text_hash=record.ocr_text_hash,
        metadata_json=record.metadata_json,
        status=SourceObjectStatus(record.status),
        trace_id=record.trace_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        deleted_at=record.deleted_at,
    )


def relationship_seed_from_record(record: RelationshipSeedRecord) -> RelationshipSeed:
    return RelationshipSeed(
        id=record.id,
        workspace_id=record.workspace_id,
        relationship_type=record.relationship_type,
        from_id=record.from_id,
        to_id=record.to_id,
        confidence=record.confidence,
        raw_event_id=record.raw_event_id,
        normalized_version=record.normalized_version,
        trace_id=record.trace_id,
    )


class SqlAlchemySourceObjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._memory = InMemorySourceObjectRepository()

    async def upsert_many(
        self, records: list[SourceObject]
    ) -> list[UpsertResult[SourceObject]]:
        results: list[UpsertResult[SourceObject]] = []
        for record in records:
            results.append(await self._upsert(record))
        await self.session.flush()
        return results

    async def get_by_id(self, source_object_id: str) -> SourceObject:
        record = await self.session.get(SourceObjectRecord, source_object_id)
        if record is None:
            raise SourceRecordNotFoundError(source_object_id)
        return source_object_from_record(record)

    async def get_by_external_identity(
        self,
        workspace_id: str,
        provider: str,
        object_type: str,
        external_object_id: str,
    ) -> SourceObject | None:
        result = await self.session.execute(
            select(SourceObjectRecord).where(
                SourceObjectRecord.workspace_id == workspace_id,
                SourceObjectRecord.provider == provider,
                SourceObjectRecord.object_type == object_type,
                SourceObjectRecord.external_object_id == external_object_id,
            )
        )
        record = result.scalar_one_or_none()
        return source_object_from_record(record) if record else None

    async def mark_stale(self, source_object_id: str) -> SourceObject:
        record = await self.get_by_id(source_object_id)
        updated = self._memory._transition(record, SourceObjectStatus.STALE)
        await self._apply_update(updated)
        return updated

    async def mark_deleted(self, source_object_id: str) -> SourceObject:
        record = await self.get_by_id(source_object_id)
        updated = self._memory._transition(
            record,
            SourceObjectStatus.DELETED,
            deleted_at=datetime.now(UTC),
        )
        await self._apply_update(updated)
        return updated

    async def _upsert(self, record: SourceObject) -> UpsertResult[SourceObject]:
        existing = await self.get_by_external_identity(
            record.workspace_id,
            record.provider,
            record.object_type,
            record.external_object_id,
        )
        if existing is None:
            self.session.add(self._record_from_source_object(record))
            return UpsertResult(record, "inserted")
        if (
            existing.content_hash == record.content_hash
            and existing.normalized_version == record.normalized_version
        ):
            return UpsertResult(existing, "noop")
        updated = record.model_copy(
            update={"id": existing.id, "created_at": existing.created_at}
        )
        await self._apply_update(updated)
        return UpsertResult(updated, "updated")

    async def _apply_update(self, source_object: SourceObject) -> None:
        record = await self.session.get(SourceObjectRecord, source_object.id)
        if record is None:
            raise SourceRecordNotFoundError(source_object.id)
        record.source_connection_id = source_object.source_connection_id
        record.provider = source_object.provider
        record.object_type = source_object.object_type
        record.external_object_id = source_object.external_object_id
        record.external_object_key = source_object.external_object_key
        record.parent_object_id = source_object.parent_object_id
        record.title = source_object.title
        record.canonical_url = source_object.canonical_url
        record.author_external_id = source_object.author_external_id
        record.occurred_at = source_object.occurred_at
        record.source_updated_at = source_object.source_updated_at
        record.normalized_version = source_object.normalized_version
        record.content_hash = source_object.content_hash
        record.content_text = source_object.content_text
        record.metadata_json = dict(source_object.metadata_json)
        record.status = SourceObjectStatus(source_object.status).value
        record.superseded_by_id = source_object.superseded_by_id
        record.deleted_at = source_object.deleted_at
        record.trace_id = source_object.trace_id
        record.updated_at = source_object.updated_at
        await self.session.flush()

    def _record_from_source_object(
        self, source_object: SourceObject
    ) -> SourceObjectRecord:
        return SourceObjectRecord(
            id=source_object.id,
            workspace_id=source_object.workspace_id,
            source_connection_id=source_object.source_connection_id,
            provider=source_object.provider,
            object_type=source_object.object_type,
            external_object_id=source_object.external_object_id,
            external_object_key=source_object.external_object_key,
            parent_object_id=source_object.parent_object_id,
            title=source_object.title,
            canonical_url=source_object.canonical_url,
            author_external_id=source_object.author_external_id,
            occurred_at=source_object.occurred_at,
            source_updated_at=source_object.source_updated_at,
            normalized_version=source_object.normalized_version,
            content_hash=source_object.content_hash,
            content_text=source_object.content_text,
            metadata_json=dict(source_object.metadata_json),
            status=SourceObjectStatus(source_object.status).value,
            superseded_by_id=source_object.superseded_by_id,
            deleted_at=source_object.deleted_at,
            trace_id=source_object.trace_id,
            created_at=source_object.created_at,
            updated_at=source_object.updated_at,
        )


class SqlAlchemySourceFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._memory = InMemorySourceFileRepository()

    async def upsert_many(
        self, records: list[SourceFile]
    ) -> list[UpsertResult[SourceFile]]:
        results: list[UpsertResult[SourceFile]] = []
        for record in records:
            results.append(await self._upsert(record))
        await self.session.flush()
        return results

    async def get_by_id(self, source_file_id: str) -> SourceFile:
        record = await self.session.get(SourceFileRecord, source_file_id)
        if record is None:
            raise SourceRecordNotFoundError(source_file_id)
        return source_file_from_record(record)

    async def get_by_external_file_id(
        self, workspace_id: str, provider: str, external_file_id: str
    ) -> SourceFile | None:
        result = await self.session.execute(
            select(SourceFileRecord).where(
                SourceFileRecord.workspace_id == workspace_id,
                SourceFileRecord.provider == provider,
                SourceFileRecord.external_file_id == external_file_id,
            )
        )
        record = result.scalar_one_or_none()
        return source_file_from_record(record) if record else None

    async def _upsert(self, record: SourceFile) -> UpsertResult[SourceFile]:
        if record.provider is None or record.external_file_id is None:
            raise NormalizationRepositoryError(
                "source files require provider and external_file_id"
            )
        existing = await self.get_by_external_file_id(
            record.workspace_id, record.provider, record.external_file_id
        )
        if existing is None:
            self.session.add(self._record_from_source_file(record))
            return UpsertResult(record, "inserted")
        if (
            existing.content_hash == record.content_hash
            and existing.ocr_text_hash == record.ocr_text_hash
        ):
            return UpsertResult(existing, "noop")
        updated = record.model_copy(
            update={"id": existing.id, "created_at": existing.created_at}
        )
        await self._apply_update(updated)
        return UpsertResult(updated, "updated")

    async def _apply_update(self, source_file: SourceFile) -> None:
        record = await self.session.get(SourceFileRecord, source_file.id)
        if record is None:
            raise SourceRecordNotFoundError(source_file.id)
        record.source_object_id = source_file.source_object_id
        record.source_connection_id = source_file.source_connection_id or ""
        record.provider = source_file.provider or ""
        record.external_file_id = source_file.external_file_id or ""
        record.external_object_key = source_file.external_object_key
        record.file_name_hash = source_file.file_name_hash
        record.content_type = source_file.content_type
        record.storage_ref = source_file.storage_ref
        record.content_hash = source_file.content_hash
        record.ocr_text = source_file.ocr_text
        record.ocr_text_hash = source_file.ocr_text_hash
        record.metadata_json = dict(source_file.metadata_json)
        record.status = SourceObjectStatus(source_file.status).value
        record.trace_id = source_file.trace_id
        record.updated_at = source_file.updated_at
        record.deleted_at = source_file.deleted_at
        await self.session.flush()

    def _record_from_source_file(self, source_file: SourceFile) -> SourceFileRecord:
        return SourceFileRecord(
            id=source_file.id,
            workspace_id=source_file.workspace_id,
            source_object_id=source_file.source_object_id,
            source_connection_id=source_file.source_connection_id or "",
            provider=source_file.provider or "",
            external_file_id=source_file.external_file_id or "",
            external_object_key=source_file.external_object_key,
            file_name_hash=source_file.file_name_hash,
            content_type=source_file.content_type,
            storage_ref=source_file.storage_ref,
            content_hash=source_file.content_hash,
            ocr_text=source_file.ocr_text,
            ocr_text_hash=source_file.ocr_text_hash,
            metadata_json=dict(source_file.metadata_json),
            status=SourceObjectStatus(source_file.status).value,
            trace_id=source_file.trace_id,
            created_at=source_file.created_at,
            updated_at=source_file.updated_at,
            deleted_at=source_file.deleted_at,
        )


class SqlAlchemyRelationshipSeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_many(
        self, records: list[RelationshipSeed]
    ) -> list[UpsertResult[RelationshipSeed]]:
        results: list[UpsertResult[RelationshipSeed]] = []
        for record in records:
            existing = await self.session.get(RelationshipSeedRecord, record.id)
            if existing is None:
                self.session.add(self._record_from_seed(record))
                results.append(UpsertResult(record, "inserted"))
                continue
            existing_seed = relationship_seed_from_record(existing)
            if existing_seed == record:
                results.append(UpsertResult(existing_seed, "noop"))
                continue
            existing.relationship_type = record.relationship_type
            existing.from_id = record.from_id
            existing.to_id = record.to_id
            existing.confidence = record.confidence
            existing.raw_event_id = record.raw_event_id
            existing.normalized_version = record.normalized_version
            existing.trace_id = record.trace_id
            results.append(UpsertResult(record, "updated"))
        await self.session.flush()
        return results

    async def list_all(self) -> list[RelationshipSeed]:
        result = await self.session.execute(select(RelationshipSeedRecord))
        return [relationship_seed_from_record(record) for record in result.scalars()]

    def _record_from_seed(self, seed: RelationshipSeed) -> RelationshipSeedRecord:
        return RelationshipSeedRecord(
            id=seed.id,
            workspace_id=seed.workspace_id,
            relationship_type=seed.relationship_type,
            from_id=seed.from_id,
            to_id=seed.to_id,
            confidence=seed.confidence,
            raw_event_id=seed.raw_event_id,
            normalized_version=seed.normalized_version,
            trace_id=seed.trace_id,
        )
