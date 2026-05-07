from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar

from cortex.contracts.entities import SourceFile, SourceObject
from cortex.contracts.enums import SourceObjectStatus

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
