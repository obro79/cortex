from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from cortex.contracts.entities import SourceChunk
from cortex.contracts.enums import SourceChunkStatus


@dataclass(frozen=True)
class ChunkUpsertResult:
    record: SourceChunk
    operation: str


class InMemorySourceChunkRepository:
    def __init__(self) -> None:
        self._records: dict[str, SourceChunk] = {}
        self._by_identity: dict[tuple[str, str, str | None, str, int, str], str] = {}

    def upsert_many(self, records: list[SourceChunk]) -> list[ChunkUpsertResult]:
        return [self._upsert(record) for record in records]

    def get_by_id(self, source_chunk_id: str) -> SourceChunk:
        return self._records[source_chunk_id]

    def list_by_source_object(
        self, workspace_id: str, source_object_id: str
    ) -> list[SourceChunk]:
        return [
            chunk
            for chunk in self._records.values()
            if chunk.workspace_id == workspace_id
            and chunk.source_object_id == source_object_id
        ]

    def search_fts(
        self,
        *,
        workspace_id: str,
        query: str,
        status: SourceChunkStatus = SourceChunkStatus.ACTIVE,
        chunking_version: str | None = None,
    ) -> list[SourceChunk]:
        terms = query.lower().split()
        return [
            chunk
            for chunk in self._records.values()
            if chunk.workspace_id == workspace_id
            and chunk.status == status
            and (chunking_version is None or chunk.chunking_version == chunking_version)
            and all(term in chunk.text.lower() for term in terms)
        ]

    def mark_stale_replaced_by(
        self,
        *,
        workspace_id: str,
        source_object_id: str,
        active_ids: set[str],
    ) -> list[SourceChunk]:
        stale = []
        for chunk in list(self._records.values()):
            if (
                chunk.workspace_id == workspace_id
                and chunk.source_object_id == source_object_id
                and chunk.id not in active_ids
                and chunk.status == SourceChunkStatus.ACTIVE
            ):
                updated = chunk.model_copy(
                    update={
                        "status": SourceChunkStatus.STALE,
                        "updated_at": datetime.now(UTC),
                    }
                )
                self._records[chunk.id] = updated
                stale.append(updated)
        return stale

    def _upsert(self, record: SourceChunk) -> ChunkUpsertResult:
        key = (
            record.workspace_id,
            record.source_object_id,
            record.source_file_id,
            record.chunk_type,
            record.chunk_index,
            record.chunking_version,
        )
        existing_id = self._by_identity.get(key)
        if existing_id is None:
            self._records[record.id] = record
            self._by_identity[key] = record.id
            return ChunkUpsertResult(record, "inserted")
        existing = self._records[existing_id]
        if (
            existing.text_hash == record.text_hash
            and existing.created_from_hash == record.created_from_hash
            and existing.status == SourceChunkStatus.ACTIVE
        ):
            return ChunkUpsertResult(existing, "noop")
        updated = record.model_copy(
            update={"id": existing.id, "created_at": existing.created_at}
        )
        self._records[existing.id] = updated
        return ChunkUpsertResult(updated, "updated")
