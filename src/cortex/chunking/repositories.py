from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.contracts.entities import SourceChunk
from cortex.contracts.enums import SourceChunkStatus
from cortex.db.models import SourceChunkRecord, SourceObjectRecord


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

    def list_all(self, workspace_id: str | None = None) -> list[SourceChunk]:
        return [
            chunk
            for chunk in self._records.values()
            if workspace_id is None or chunk.workspace_id == workspace_id
        ]

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
        source_chunk_ids: set[str] | None = None,
    ) -> list[SourceChunk]:
        filters_requested = any(
            item is not None
            for item in (source_object_ids, source_file_ids, source_chunk_ids)
        )
        return [
            chunk
            for chunk in self._records.values()
            if chunk.workspace_id == workspace_id
            and (
                not filters_requested
                or (
                    source_object_ids is not None
                    and chunk.source_object_id in source_object_ids
                )
                or (
                    source_file_ids is not None
                    and chunk.source_file_id is not None
                    and chunk.source_file_id in source_file_ids
                )
                or (source_chunk_ids is not None and chunk.id in source_chunk_ids)
            )
        ]

    def search_fts(
        self,
        *,
        workspace_id: str,
        query: str,
        status: SourceChunkStatus = SourceChunkStatus.ACTIVE,
        chunking_version: str | None = None,
        source_allowlist: Iterable[str] = (),
        provider_filters: Iterable[str] = (),
    ) -> list[SourceChunk]:
        terms = query.lower().split()
        allowed_sources = {value for value in source_allowlist if value}
        allowed_providers = {
            value.lower() for value in provider_filters if value.strip()
        }
        return [
            chunk
            for chunk in self._records.values()
            if chunk.workspace_id == workspace_id
            and chunk.status == status
            and (chunking_version is None or chunk.chunking_version == chunking_version)
            and (not allowed_sources or chunk.source_object_id in allowed_sources)
            and (
                not allowed_providers
                or _provider_from_metadata(chunk.metadata_json) in allowed_providers
            )
            and all(term in chunk.text.lower() for term in terms)
        ]

    def search_fts_ranked(
        self,
        *,
        workspace_id: str,
        query: str,
        status: SourceChunkStatus = SourceChunkStatus.ACTIVE,
        chunking_version: str | None = None,
        source_allowlist: Iterable[str] = (),
        provider_filters: Iterable[str] = (),
        limit: int | None = None,
    ) -> list[tuple[SourceChunk, float]]:
        """Deterministic fixture stand-in for the production FTS contract.

        PostgreSQL ranking is implemented by ``SqlAlchemySourceChunkRepository``.
        This intentionally only provides a stable, token-based score for unit tests.
        """
        terms = [term for term in query.lower().split() if term]
        if not terms:
            return []
        matches = self.search_fts(
            workspace_id=workspace_id,
            query=query,
            status=status,
            chunking_version=chunking_version,
            source_allowlist=source_allowlist,
            provider_filters=provider_filters,
        )
        ranked = [
            (chunk, sum(chunk.text.lower().count(term) for term in terms) / len(terms))
            for chunk in matches
        ]
        ranked.sort(key=lambda item: (-item[1], item[0].id))
        return ranked[:limit] if limit is not None else ranked

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

    def mark_deleted_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
        source_chunk_ids: set[str] | None = None,
    ) -> list[SourceChunk]:
        deleted: list[SourceChunk] = []
        for chunk in self.list_for_lifecycle(
            workspace_id=workspace_id,
            source_object_ids=source_object_ids,
            source_file_ids=source_file_ids,
            source_chunk_ids=source_chunk_ids,
        ):
            if chunk.status == SourceChunkStatus.DELETED:
                continue
            updated = chunk.model_copy(
                update={
                    "status": SourceChunkStatus.DELETED,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._records[chunk.id] = updated
            deleted.append(updated)
        return deleted

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


def source_chunk_from_record(record: SourceChunkRecord) -> SourceChunk:
    return SourceChunk(
        id=record.id,
        workspace_id=record.workspace_id,
        source_object_id=record.source_object_id,
        source_file_id=record.source_file_id,
        chunk_type=record.chunk_type,
        chunk_index=record.chunk_index,
        text=record.text,
        text_hash=record.text_hash,
        token_count=record.token_count,
        chunking_version=record.chunking_version,
        citation_label=record.citation_label,
        citation_url=record.citation_url,
        metadata_json=record.metadata_json,
        status=SourceChunkStatus(record.status),
        created_from_hash=record.created_from_hash,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemySourceChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_many(self, records: list[SourceChunk]) -> list[ChunkUpsertResult]:
        results: list[ChunkUpsertResult] = []
        for record in records:
            results.append(await self._upsert(record))
        await self.session.flush()
        return results

    async def get_by_id(self, source_chunk_id: str) -> SourceChunk:
        record = await self.session.get(SourceChunkRecord, source_chunk_id)
        if record is None:
            raise KeyError(source_chunk_id)
        return source_chunk_from_record(record)

    async def list_by_source_object(
        self, workspace_id: str, source_object_id: str
    ) -> list[SourceChunk]:
        result = await self.session.execute(
            select(SourceChunkRecord)
            .where(
                SourceChunkRecord.workspace_id == workspace_id,
                SourceChunkRecord.source_object_id == source_object_id,
            )
            .order_by(SourceChunkRecord.chunk_index, SourceChunkRecord.id)
        )
        return [source_chunk_from_record(record) for record in result.scalars()]

    async def list_all(self, workspace_id: str | None = None) -> list[SourceChunk]:
        statement = select(SourceChunkRecord)
        if workspace_id is not None:
            statement = statement.where(SourceChunkRecord.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return [source_chunk_from_record(record) for record in result.scalars()]

    async def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
        source_chunk_ids: set[str] | None = None,
    ) -> list[SourceChunk]:
        statement = select(SourceChunkRecord).where(
            SourceChunkRecord.workspace_id == workspace_id
        )
        filters = []
        if source_object_ids is not None:
            filters.append(SourceChunkRecord.source_object_id.in_(source_object_ids))
        if source_file_ids is not None:
            filters.append(SourceChunkRecord.source_file_id.in_(source_file_ids))
        if source_chunk_ids is not None:
            filters.append(SourceChunkRecord.id.in_(source_chunk_ids))
        if filters:
            statement = statement.where(or_(*filters))
        result = await self.session.execute(statement)
        return [source_chunk_from_record(record) for record in result.scalars()]

    async def search_fts(
        self,
        *,
        workspace_id: str,
        query: str,
        status: SourceChunkStatus = SourceChunkStatus.ACTIVE,
        chunking_version: str | None = None,
        source_allowlist: Iterable[str] = (),
        provider_filters: Iterable[str] = (),
    ) -> list[SourceChunk]:
        ranked = await self.search_fts_ranked(
            workspace_id=workspace_id,
            query=query,
            status=status,
            chunking_version=chunking_version,
            source_allowlist=source_allowlist,
            provider_filters=provider_filters,
        )
        return [chunk for chunk, _score in ranked]

    async def search_fts_ranked(
        self,
        *,
        workspace_id: str,
        query: str,
        status: SourceChunkStatus = SourceChunkStatus.ACTIVE,
        chunking_version: str | None = None,
        source_allowlist: Iterable[str] = (),
        provider_filters: Iterable[str] = (),
        limit: int | None = None,
    ) -> list[tuple[SourceChunk, float]]:
        """Run ranked PostgreSQL full-text search without interpolating user input."""
        if not query.strip():
            return []
        vector = func.to_tsvector("english", SourceChunkRecord.text)
        tsquery = func.websearch_to_tsquery("english", query)
        rank = func.ts_rank_cd(vector, tsquery).label("lexical_score")
        allowed_sources = {value for value in source_allowlist if value}
        allowed_providers = {
            value.lower() for value in provider_filters if value.strip()
        }
        statement = (
            select(SourceChunkRecord, rank)
            .where(
                SourceChunkRecord.workspace_id == workspace_id,
                SourceChunkRecord.status == SourceChunkStatus(status).value,
                vector.op("@@")(tsquery),
            )
            .order_by(rank.desc(), SourceChunkRecord.id)
        )
        if chunking_version is not None:
            statement = statement.where(
                SourceChunkRecord.chunking_version == chunking_version
            )
        if allowed_sources:
            statement = statement.where(
                SourceChunkRecord.source_object_id.in_(allowed_sources)
            )
        if allowed_providers:
            statement = statement.join(
                SourceObjectRecord,
                and_(
                    SourceObjectRecord.workspace_id == SourceChunkRecord.workspace_id,
                    SourceObjectRecord.id == SourceChunkRecord.source_object_id,
                ),
            ).where(
                func.lower(SourceObjectRecord.provider).in_(allowed_providers),
            )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self.session.execute(statement)
        return [
            (source_chunk_from_record(record), float(score))
            for record, score in result.tuples()
        ]

    async def mark_stale_replaced_by(
        self,
        *,
        workspace_id: str,
        source_object_id: str,
        active_ids: set[str],
    ) -> list[SourceChunk]:
        result = await self.session.execute(
            select(SourceChunkRecord).where(
                SourceChunkRecord.workspace_id == workspace_id,
                SourceChunkRecord.source_object_id == source_object_id,
                SourceChunkRecord.status == SourceChunkStatus.ACTIVE.value,
            )
        )
        stale: list[SourceChunk] = []
        now = datetime.now(UTC)
        for record in result.scalars():
            if record.id in active_ids:
                continue
            record.status = SourceChunkStatus.STALE.value
            record.updated_at = now
            stale.append(source_chunk_from_record(record))
        await self.session.flush()
        return stale

    async def mark_deleted_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
        source_chunk_ids: set[str] | None = None,
    ) -> list[SourceChunk]:
        chunks = await self.list_for_lifecycle(
            workspace_id=workspace_id,
            source_object_ids=source_object_ids,
            source_file_ids=source_file_ids,
            source_chunk_ids=source_chunk_ids,
        )
        ids = {
            chunk.id for chunk in chunks if chunk.status != SourceChunkStatus.DELETED
        }
        if not ids:
            return []
        now = datetime.now(UTC)
        await self.session.execute(
            update(SourceChunkRecord)
            .where(SourceChunkRecord.id.in_(ids))
            .values(status=SourceChunkStatus.DELETED.value, updated_at=now)
        )
        await self.session.flush()
        return [
            chunk.model_copy(
                update={"status": SourceChunkStatus.DELETED, "updated_at": now}
            )
            for chunk in chunks
            if chunk.id in ids
        ]

    async def _upsert(self, record: SourceChunk) -> ChunkUpsertResult:
        existing = await self._get_by_identity(record)
        if existing is None:
            self.session.add(self._record_from_source_chunk(record))
            return ChunkUpsertResult(record, "inserted")
        if (
            existing.text_hash == record.text_hash
            and existing.created_from_hash == record.created_from_hash
            and existing.status == SourceChunkStatus.ACTIVE
        ):
            return ChunkUpsertResult(existing, "noop")
        updated = record.model_copy(
            update={"id": existing.id, "created_at": existing.created_at}
        )
        await self._apply_update(updated)
        return ChunkUpsertResult(updated, "updated")

    async def _get_by_identity(self, chunk: SourceChunk) -> SourceChunk | None:
        result = await self.session.execute(
            select(SourceChunkRecord).where(
                SourceChunkRecord.workspace_id == chunk.workspace_id,
                SourceChunkRecord.source_object_id == chunk.source_object_id,
                SourceChunkRecord.source_file_id == chunk.source_file_id,
                SourceChunkRecord.chunk_type == chunk.chunk_type,
                SourceChunkRecord.chunk_index == chunk.chunk_index,
                SourceChunkRecord.chunking_version == chunk.chunking_version,
            )
        )
        record = result.scalar_one_or_none()
        return source_chunk_from_record(record) if record else None

    async def _apply_update(self, chunk: SourceChunk) -> None:
        record = await self.session.get(SourceChunkRecord, chunk.id)
        if record is None:
            raise KeyError(chunk.id)
        record.source_object_id = chunk.source_object_id
        record.source_file_id = chunk.source_file_id
        record.chunk_type = chunk.chunk_type
        record.chunk_index = chunk.chunk_index
        record.text = chunk.text
        record.text_hash = chunk.text_hash
        record.token_count = chunk.token_count
        record.chunking_version = chunk.chunking_version
        record.citation_label = chunk.citation_label
        record.citation_url = chunk.citation_url
        record.metadata_json = dict(chunk.metadata_json)
        record.status = SourceChunkStatus(chunk.status).value
        record.created_from_hash = chunk.created_from_hash
        record.updated_at = chunk.updated_at
        await self.session.flush()

    def _record_from_source_chunk(self, chunk: SourceChunk) -> SourceChunkRecord:
        return SourceChunkRecord(
            id=chunk.id,
            workspace_id=chunk.workspace_id,
            source_object_id=chunk.source_object_id,
            source_file_id=chunk.source_file_id,
            chunk_type=chunk.chunk_type,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            text_hash=chunk.text_hash,
            token_count=chunk.token_count,
            chunking_version=chunk.chunking_version,
            citation_label=chunk.citation_label,
            citation_url=chunk.citation_url,
            metadata_json=dict(chunk.metadata_json),
            status=SourceChunkStatus(chunk.status).value,
            created_from_hash=chunk.created_from_hash,
            created_at=chunk.created_at,
            updated_at=chunk.updated_at,
        )


def _provider_from_metadata(metadata: dict[str, object]) -> str | None:
    provider = metadata.get("provider")
    if isinstance(provider, str):
        return provider.lower()
    object_type = metadata.get("object_type")
    provider_by_object_type = {
        "slack_thread": "slack",
        "linear_issue": "linear",
        "github_pull_request": "github",
        "github_issue": "github",
        "github_commit": "github",
        "repo_doc": "repo_docs",
    }
    if not isinstance(object_type, str):
        return None
    return provider_by_object_type.get(object_type)
