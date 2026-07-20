from __future__ import annotations

from collections.abc import Awaitable, Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

from cortex.contracts.entities import (
    EmbeddingRecord,
    IndexJob,
    RawEvent,
    SourceChunk,
    SourceFile,
    SourceObject,
)
from cortex.contracts.enums import (
    EmbeddingJobStatus,
    IndexJobStatus,
    RawEventStatus,
    SourceChunkStatus,
    SourceObjectStatus,
)
from cortex.indexing.qdrant import qdrant_point_id
from cortex.ingestion.payloads import PayloadStore
from cortex.lifecycle.models import LifecycleExportResult
from cortex.utils.asyncio import maybe_await


class LifecycleVectorDeleter(Protocol):
    def delete_point(
        self, collection: str, point_id: str
    ) -> bool | Awaitable[bool]: ...


class ExportableRecord(Protocol):
    def model_dump(self, *, mode: str) -> dict[str, object]: ...


class LifecycleListRepository(Protocol):
    def list_all(
        self, workspace_id: str | None = None
    ) -> Sequence[ExportableRecord] | Awaitable[Sequence[ExportableRecord]]: ...


class LifecycleRawEventRepository(LifecycleListRepository, Protocol):
    def list_all(
        self, workspace_id: str | None = None
    ) -> Sequence[RawEvent] | Awaitable[Sequence[RawEvent]]: ...

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_connection_id: str | None = None,
        raw_event_ids: set[str] | None = None,
        external_object_keys: set[str] | None = None,
    ) -> list[RawEvent] | Awaitable[list[RawEvent]]: ...

    def mark_deleted_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_connection_id: str | None = None,
        raw_event_ids: set[str] | None = None,
        external_object_keys: set[str] | None = None,
    ) -> list[RawEvent] | Awaitable[list[RawEvent]]: ...


class LifecycleSourceObjectRepository(LifecycleListRepository, Protocol):
    def list_all(
        self, workspace_id: str | None = None
    ) -> Sequence[SourceObject] | Awaitable[Sequence[SourceObject]]: ...

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_connection_id: str | None = None,
    ) -> list[SourceObject] | Awaitable[list[SourceObject]]: ...

    def mark_deleted_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_connection_id: str | None = None,
    ) -> list[SourceObject] | Awaitable[list[SourceObject]]: ...


class LifecycleSourceFileRepository(LifecycleListRepository, Protocol):
    def list_all(
        self, workspace_id: str | None = None
    ) -> Sequence[SourceFile] | Awaitable[Sequence[SourceFile]]: ...

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
        source_connection_id: str | None = None,
    ) -> list[SourceFile] | Awaitable[list[SourceFile]]: ...

    def mark_deleted_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
    ) -> list[SourceFile] | Awaitable[list[SourceFile]]: ...


class LifecycleSourceChunkRepository(LifecycleListRepository, Protocol):
    def list_all(
        self, workspace_id: str | None = None
    ) -> Sequence[SourceChunk] | Awaitable[Sequence[SourceChunk]]: ...

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
        source_chunk_ids: set[str] | None = None,
    ) -> list[SourceChunk] | Awaitable[list[SourceChunk]]: ...

    def mark_deleted_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_object_ids: set[str] | None = None,
        source_file_ids: set[str] | None = None,
        source_chunk_ids: set[str] | None = None,
    ) -> list[SourceChunk] | Awaitable[list[SourceChunk]]: ...


class LifecycleEmbeddingRepository(LifecycleListRepository, Protocol):
    def list_all(
        self, workspace_id: str | None = None
    ) -> Sequence[EmbeddingRecord] | Awaitable[Sequence[EmbeddingRecord]]: ...

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_chunk_ids: set[str] | None = None,
        embedding_ids: set[str] | None = None,
    ) -> list[EmbeddingRecord] | Awaitable[list[EmbeddingRecord]]: ...

    def mark_stale_for_lifecycle(
        self,
        *,
        workspace_id: str,
        source_chunk_ids: set[str] | None = None,
        embedding_ids: set[str] | None = None,
    ) -> list[EmbeddingRecord] | Awaitable[list[EmbeddingRecord]]: ...


class LifecycleIndexJobRepository(LifecycleListRepository, Protocol):
    def list_all(
        self, workspace_id: str | None = None
    ) -> Sequence[IndexJob] | Awaitable[Sequence[IndexJob]]: ...

    def list_for_lifecycle(
        self,
        *,
        workspace_id: str,
        target_type: str | None = None,
        target_ids: set[str] | None = None,
    ) -> list[IndexJob] | Awaitable[list[IndexJob]]: ...

    def mark_stale_for_lifecycle(
        self,
        *,
        workspace_id: str,
        target_type: str | None = None,
        target_ids: set[str] | None = None,
    ) -> list[IndexJob] | Awaitable[list[IndexJob]]: ...


@dataclass(frozen=True)
class InMemoryVectorLifecycleDeleter:
    points: dict[str, dict[str, object]]

    def delete_point(self, collection: str, point_id: str) -> bool:
        collection_points = self.points.get(collection)
        if collection_points is None or point_id not in collection_points:
            return False
        del collection_points[point_id]
        return True


@dataclass(frozen=True)
class QdrantLifecycleDeleter:
    base_url: str
    api_key: str | None = None
    timeout_seconds: float = 10.0

    async def delete_point(self, collection: str, point_id: str) -> bool:
        headers = {"api-key": self.api_key} if self.api_key else None
        async with httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"),
            headers=headers,
            timeout=self.timeout_seconds,
        ) as client:
            response = await client.post(
                f"/collections/{collection}/points/delete",
                json={"points": [qdrant_point_id(collection, point_id)]},
            )
        return 200 <= response.status_code < 300


@dataclass(frozen=True)
class LifecycleRecordSelection:
    raw_events: list[RawEvent]
    source_objects: list[SourceObject]
    source_files: list[SourceFile]
    source_chunks: list[SourceChunk]
    embeddings: list[EmbeddingRecord]
    index_jobs: list[IndexJob]


class RepositoryLifecycleDeletionExecutor:
    """Deletes persisted lifecycle data through repository APIs.

    The executor intentionally returns counts per store. The tombstone records
    those counts so failed or partial compliance work can be repaired without
    exposing raw target IDs in the tombstone itself.
    """

    def __init__(
        self,
        *,
        raw_events: LifecycleRawEventRepository | None = None,
        source_objects: LifecycleSourceObjectRepository | None = None,
        source_files: LifecycleSourceFileRepository | None = None,
        source_chunks: LifecycleSourceChunkRepository | None = None,
        embeddings: LifecycleEmbeddingRepository | None = None,
        index_jobs: LifecycleIndexJobRepository | None = None,
        payload_store: PayloadStore | None = None,
        vector_deleter: LifecycleVectorDeleter | None = None,
    ) -> None:
        self.raw_events = raw_events
        self.source_objects = source_objects
        self.source_files = source_files
        self.source_chunks = source_chunks
        self.embeddings = embeddings
        self.index_jobs = index_jobs
        self.payload_store = payload_store
        self.vector_deleter = vector_deleter

    async def delete(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
    ) -> dict[str, int]:
        selection = await self._select(
            workspace_id=workspace_id,
            target_type=target_type,
            target_id=target_id,
        )
        payload_refs = sorted(
            set(_payload_refs(selection.raw_events, selection.source_files))
        )
        vector_points = [
            (embedding.qdrant_collection, embedding.qdrant_point_id)
            for embedding in selection.embeddings
            if embedding.qdrant_collection and embedding.qdrant_point_id
        ]
        source_object_ids = {record.id for record in selection.source_objects}
        source_file_ids = {record.id for record in selection.source_files}
        source_chunk_ids = {record.id for record in selection.source_chunks}
        embedding_ids = {record.id for record in selection.embeddings}
        index_job_target_ids = {record.target_id for record in selection.index_jobs}
        expected_counts = _expected_counts(
            selection=selection,
            vector_points=vector_points,
            payload_refs=payload_refs,
        )

        vector_deleted = 0
        if self.vector_deleter is not None:
            for collection, point_id in vector_points:
                if await maybe_await(
                    self.vector_deleter.delete_point(collection, point_id)
                ):
                    vector_deleted += 1

        payload_deleted = 0
        payload_skipped = 0
        if self.payload_store is not None:
            for payload_ref in payload_refs:
                try:
                    if self.payload_store.delete(payload_ref):
                        payload_deleted += 1
                    else:
                        payload_skipped += 1
                except Exception:
                    payload_skipped += 1
        else:
            payload_skipped = len(payload_refs)

        stale_embeddings = []
        if self.embeddings is not None and embedding_ids:
            stale_embeddings = await maybe_await(
                self.embeddings.mark_stale_for_lifecycle(
                    workspace_id=workspace_id,
                    embedding_ids=embedding_ids,
                )
            )

        stale_index_jobs = []
        if self.index_jobs is not None and index_job_target_ids:
            stale_index_jobs = await maybe_await(
                self.index_jobs.mark_stale_for_lifecycle(
                    workspace_id=workspace_id,
                    target_type="source_chunk",
                    target_ids=index_job_target_ids,
                )
            )

        deleted_chunks = []
        if self.source_chunks is not None and source_chunk_ids:
            deleted_chunks = await maybe_await(
                self.source_chunks.mark_deleted_for_lifecycle(
                    workspace_id=workspace_id,
                    source_chunk_ids=source_chunk_ids,
                )
            )

        deleted_files = []
        if self.source_files is not None and source_file_ids:
            deleted_files = await maybe_await(
                self.source_files.mark_deleted_for_lifecycle(
                    workspace_id=workspace_id,
                    source_file_ids=source_file_ids,
                )
            )

        deleted_objects = []
        if self.source_objects is not None and source_object_ids:
            deleted_objects = await maybe_await(
                self.source_objects.mark_deleted_for_lifecycle(
                    workspace_id=workspace_id,
                    source_object_ids=source_object_ids,
                )
            )

        deleted_raw_events = []
        raw_event_ids = {record.id for record in selection.raw_events}
        if self.raw_events is not None and raw_event_ids:
            deleted_raw_events = await maybe_await(
                self.raw_events.mark_deleted_for_lifecycle(
                    workspace_id=workspace_id,
                    raw_event_ids=raw_event_ids,
                )
            )

        return {
            "raw_events": len(deleted_raw_events),
            "source_objects": len(deleted_objects),
            "source_files": len(deleted_files),
            "source_chunks": len(deleted_chunks),
            "embeddings": len(stale_embeddings),
            "index_jobs": len(stale_index_jobs),
            "vector_points": vector_deleted,
            "payload_refs_deleted": payload_deleted,
            "payload_refs_skipped": payload_skipped,
            **expected_counts,
        }

    async def _select(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
    ) -> LifecycleRecordSelection:
        source_objects = await self._source_objects(
            workspace_id,
            target_type,
            target_id,
        )
        source_object_ids = {record.id for record in source_objects}
        source_files = await self._source_files(
            workspace_id, target_type, target_id, source_object_ids
        )
        source_file_ids = {record.id for record in source_files}
        source_chunks = await self._source_chunks(
            workspace_id,
            target_type,
            target_id,
            source_object_ids,
            source_file_ids,
        )
        source_chunk_ids = {record.id for record in source_chunks}
        embeddings = await self._embeddings(
            workspace_id,
            target_type,
            target_id,
            source_chunk_ids,
        )
        index_jobs = await self._index_jobs(workspace_id, source_chunk_ids)
        raw_events = await self._raw_events(
            workspace_id, target_type, target_id, source_objects
        )
        return LifecycleRecordSelection(
            raw_events=raw_events,
            source_objects=source_objects,
            source_files=source_files,
            source_chunks=source_chunks,
            embeddings=embeddings,
            index_jobs=index_jobs,
        )

    async def _source_objects(
        self,
        workspace_id: str,
        target_type: str,
        target_id: str,
    ) -> list[SourceObject]:
        if self.source_objects is None:
            return []
        if target_type == "workspace":
            return list(await maybe_await(self.source_objects.list_all(workspace_id)))
        if target_type == "source_connection":
            return await maybe_await(
                self.source_objects.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_connection_id=target_id,
                )
            )
        if target_type == "source_object":
            return await maybe_await(
                self.source_objects.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_object_ids={target_id},
                )
            )
        return []

    async def _source_files(
        self,
        workspace_id: str,
        target_type: str,
        target_id: str,
        source_object_ids: set[str],
    ) -> list[SourceFile]:
        if self.source_files is None:
            return []
        if target_type == "workspace":
            return list(await maybe_await(self.source_files.list_all(workspace_id)))
        if target_type == "source_connection":
            return await maybe_await(
                self.source_files.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_connection_id=target_id,
                )
            )
        if target_type == "source_file":
            return await maybe_await(
                self.source_files.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_file_ids={target_id},
                )
            )
        if source_object_ids:
            return await maybe_await(
                self.source_files.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_object_ids=source_object_ids,
                )
            )
        return []

    async def _source_chunks(
        self,
        workspace_id: str,
        target_type: str,
        target_id: str,
        source_object_ids: set[str],
        source_file_ids: set[str],
    ) -> list[SourceChunk]:
        if self.source_chunks is None:
            return []
        if target_type == "workspace":
            return list(await maybe_await(self.source_chunks.list_all(workspace_id)))
        if target_type == "source_chunk":
            return await maybe_await(
                self.source_chunks.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_chunk_ids={target_id},
                )
            )
        if source_object_ids or source_file_ids:
            return await maybe_await(
                self.source_chunks.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_object_ids=source_object_ids or None,
                    source_file_ids=source_file_ids or None,
                )
            )
        return []

    async def _embeddings(
        self,
        workspace_id: str,
        target_type: str,
        target_id: str,
        source_chunk_ids: set[str],
    ) -> list[EmbeddingRecord]:
        if self.embeddings is None:
            return []
        if target_type == "workspace":
            return list(await maybe_await(self.embeddings.list_all(workspace_id)))
        if target_type == "embedding":
            return await maybe_await(
                self.embeddings.list_for_lifecycle(
                    workspace_id=workspace_id,
                    embedding_ids={target_id},
                )
            )
        if source_chunk_ids:
            return await maybe_await(
                self.embeddings.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_chunk_ids=source_chunk_ids,
                )
            )
        return []

    async def _index_jobs(
        self,
        workspace_id: str,
        source_chunk_ids: set[str],
    ) -> list[IndexJob]:
        if self.index_jobs is None or not source_chunk_ids:
            return []
        return await maybe_await(
            self.index_jobs.list_for_lifecycle(
                workspace_id=workspace_id,
                target_type="source_chunk",
                target_ids=source_chunk_ids,
            )
        )

    async def _raw_events(
        self,
        workspace_id: str,
        target_type: str,
        target_id: str,
        source_objects: list[SourceObject],
    ) -> list[RawEvent]:
        if self.raw_events is None:
            return []
        if target_type == "workspace":
            return list(await maybe_await(self.raw_events.list_all(workspace_id)))
        if target_type == "source_connection":
            return await maybe_await(
                self.raw_events.list_for_lifecycle(
                    workspace_id=workspace_id,
                    source_connection_id=target_id,
                )
            )
        if target_type == "raw_event":
            return await maybe_await(
                self.raw_events.list_for_lifecycle(
                    workspace_id=workspace_id,
                    raw_event_ids={target_id},
                )
            )
        external_keys = {record.external_object_key for record in source_objects}
        if external_keys:
            return await maybe_await(
                self.raw_events.list_for_lifecycle(
                    workspace_id=workspace_id,
                    external_object_keys=external_keys,
                )
            )
        return []


class RepositoryLifecycleExportExecutor:
    def __init__(
        self,
        *,
        export_store: PayloadStore,
        raw_events: LifecycleListRepository | None = None,
        source_objects: LifecycleListRepository | None = None,
        source_files: LifecycleListRepository | None = None,
        source_chunks: LifecycleListRepository | None = None,
        embeddings: LifecycleListRepository | None = None,
        index_jobs: LifecycleListRepository | None = None,
    ) -> None:
        self.export_store = export_store
        self.raw_events = raw_events
        self.source_objects = source_objects
        self.source_files = source_files
        self.source_chunks = source_chunks
        self.embeddings = embeddings
        self.index_jobs = index_jobs

    async def export(
        self,
        *,
        workspace_id: str,
        export_scope: str,
    ) -> LifecycleExportResult:
        if export_scope != "workspace":
            raise ValueError("only workspace export scope is currently supported")
        records: dict[str, list[dict[str, object]]] = {
            "raw_events": await _dump_all(self.raw_events, workspace_id),
            "source_objects": await _dump_all(self.source_objects, workspace_id),
            "source_files": await _dump_all(self.source_files, workspace_id),
            "source_chunks": await _dump_all(self.source_chunks, workspace_id),
            "embeddings": await _dump_all(self.embeddings, workspace_id),
            "index_jobs": await _dump_all(self.index_jobs, workspace_id),
        }
        counts = {name: len(items) for name, items in records.items()}
        payload_refs = sorted(
            {
                ref
                for ref in _payload_refs_from_export_records(
                    records["raw_events"],
                    records["source_files"],
                )
            }
        )
        stored = self.export_store.put_json(
            {
                "manifest": {
                    "workspace_id": workspace_id,
                    "export_scope": export_scope,
                    "counts": counts,
                    "payload_refs": payload_refs,
                },
                "records": records,
            }
        )
        return LifecycleExportResult(
            destination_ref=stored.payload_ref,
            metadata_json={
                "counts": counts,
                "payload_ref_count": len(payload_refs),
                "payload_hash": stored.payload_hash,
            },
        )


def _payload_refs(
    raw_events: list[RawEvent],
    source_files: list[SourceFile],
) -> list[str]:
    refs: list[str] = []
    refs.extend(event.payload_ref for event in raw_events if event.payload_ref)
    refs.extend(
        source_file.storage_ref
        for source_file in source_files
        if source_file.storage_ref
    )
    return refs


def _expected_counts(
    *,
    selection: LifecycleRecordSelection,
    vector_points: list[tuple[str, str]],
    payload_refs: list[str],
) -> dict[str, int]:
    return {
        "expected_raw_events": sum(
            1
            for record in selection.raw_events
            if record.status != RawEventStatus.DELETED
        ),
        "expected_source_objects": sum(
            1
            for record in selection.source_objects
            if record.status != SourceObjectStatus.DELETED
        ),
        "expected_source_files": sum(
            1
            for record in selection.source_files
            if record.status != SourceObjectStatus.DELETED
        ),
        "expected_source_chunks": sum(
            1
            for record in selection.source_chunks
            if record.status != SourceChunkStatus.DELETED
        ),
        "expected_embeddings": sum(
            1
            for record in selection.embeddings
            if record.status != EmbeddingJobStatus.STALE
        ),
        "expected_index_jobs": sum(
            1
            for record in selection.index_jobs
            if record.status != IndexJobStatus.STALE
        ),
        "expected_vector_points": len(vector_points),
        "expected_payload_refs": len(payload_refs),
    }


def _payload_refs_from_export_records(
    raw_events: list[dict[str, object]],
    source_files: list[dict[str, object]],
) -> list[str]:
    refs: list[str] = []
    refs.extend(
        str(record["payload_ref"]) for record in raw_events if record.get("payload_ref")
    )
    refs.extend(
        str(record["storage_ref"])
        for record in source_files
        if record.get("storage_ref")
    )
    return refs


async def _dump_all(
    repository: LifecycleListRepository | None,
    workspace_id: str,
) -> list[dict[str, object]]:
    if repository is None:
        return []
    records = await maybe_await(repository.list_all(workspace_id))
    return [record.model_dump(mode="json") for record in records]
