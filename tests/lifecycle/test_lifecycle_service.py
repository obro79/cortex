import json
from datetime import UTC, datetime

import pytest

from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.contracts.entities import SourceChunk, SourceFile, SourceObject
from cortex.contracts.enums import SourceChunkStatus, SourceObjectStatus
from cortex.embeddings.repositories import InMemoryEmbeddingRecordRepository
from cortex.indexing.repositories import InMemoryIndexJobRepository
from cortex.indexing.vector_memory import InMemoryVectorIndex
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadNotFoundError
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.lifecycle import (
    InMemoryLifecycleRepository,
    InMemoryVectorLifecycleDeleter,
    LifecycleActionStatus,
    LifecycleService,
    RepositoryLifecycleDeletionExecutor,
    RepositoryLifecycleExportExecutor,
    RetentionPolicy,
)
from cortex.normalization.repositories import (
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
)
from cortex.security.audit import InMemoryAuditLogRepository


class RecordingDeletionExecutor:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def delete(
        self,
        *,
        workspace_id: str,
        target_type: str,
        target_id: str,
    ) -> dict[str, int]:
        self.calls.append(
            {
                "workspace_id": workspace_id,
                "target_type": target_type,
                "target_id": target_id,
            }
        )
        return {"source_objects": 2, "source_chunks": 5, "embeddings": 5}


class AsyncLifecycleRepository(InMemoryLifecycleRepository):
    async def set_retention_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        return super().set_retention_policy(policy)


@pytest.mark.asyncio
async def test_retention_policy_builds_sweep_plan_and_audits_config() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = LifecycleService(InMemoryLifecycleRepository(), audit_log=audit_log)

    policy = await service.configure_retention(
        policy=RetentionPolicy(
            workspace_id="ws_1",
            raw_event_days=30,
            payload_days=7,
            audit_log_days=None,
            tombstone_days=365,
        ),
        actor_id="usr_1",
    )
    plan = await service.plan_retention_sweep(
        workspace_id="ws_1",
        now=datetime(2026, 5, 14, tzinfo=UTC),
    )

    assert policy.updated_at is not None
    assert plan.raw_events_before == datetime(2026, 4, 14, tzinfo=UTC)
    assert plan.payloads_before == datetime(2026, 5, 7, tzinfo=UTC)
    assert plan.audit_logs_before is None
    assert audit_log.list_for_workspace("ws_1")[0].action == (
        "lifecycle.retention.configure"
    )


@pytest.mark.asyncio
async def test_async_lifecycle_repository_is_awaited() -> None:
    service = LifecycleService(AsyncLifecycleRepository())

    policy = await service.configure_retention(
        policy=RetentionPolicy(workspace_id="ws_async", raw_event_days=14),
        actor_id="usr_1",
    )

    assert policy.workspace_id == "ws_async"
    assert policy.updated_at is not None


@pytest.mark.asyncio
async def test_deletion_request_creates_hashed_tombstone_and_audit() -> None:
    audit_log = InMemoryAuditLogRepository()
    service = LifecycleService(InMemoryLifecycleRepository(), audit_log=audit_log)

    tombstone = await service.request_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_secret",
        requested_by_user_id="usr_1",
        reason="customer_request",
    )

    record = audit_log.list_for_workspace("ws_1")[0]
    assert tombstone.status == LifecycleActionStatus.REQUESTED
    assert tombstone.target_id_hash.startswith("sha256:")
    assert tombstone.target_id_hash != "src_secret"
    assert record.target_id_hash is not None
    assert record.reason == "customer_request"


@pytest.mark.asyncio
async def test_execute_deletion_completes_tombstone() -> None:
    audit_log = InMemoryAuditLogRepository()
    repo = InMemoryLifecycleRepository()
    service = LifecycleService(repo, audit_log=audit_log)
    executor = RecordingDeletionExecutor()

    tombstone = await service.execute_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_1",
        requested_by_user_id="usr_1",
        reason="customer_request",
        executor=executor,
    )

    assert executor.calls == [
        {
            "workspace_id": "ws_1",
            "target_type": "source_connection",
            "target_id": "src_1",
        }
    ]
    assert tombstone.status == LifecycleActionStatus.COMPLETED
    assert tombstone.metadata_json["deleted_counts_json"] == {
        "source_objects": 2,
        "source_chunks": 5,
        "embeddings": 5,
    }
    assert [record.action for record in audit_log.list_for_workspace("ws_1")] == [
        "lifecycle.deletion.request",
        "lifecycle.deletion.complete",
    ]


@pytest.mark.asyncio
async def test_export_job_lifecycle() -> None:
    repo = InMemoryLifecycleRepository()
    service = LifecycleService(repo)

    job = await service.request_export(
        workspace_id="ws_1",
        requested_by_user_id="usr_1",
        export_scope="workspace",
    )
    completed = repo.complete_export_job(
        job_id=job.id,
        destination_ref="s3://exports/ws_1/export.jsonl",
    )

    assert job.status == LifecycleActionStatus.REQUESTED
    assert completed.status == LifecycleActionStatus.COMPLETED
    assert completed.destination_ref == "s3://exports/ws_1/export.jsonl"


@pytest.mark.asyncio
async def test_repository_deletion_executor_deletes_source_connection_graph() -> None:
    graph = _seed_lifecycle_graph()
    vector_index = InMemoryVectorIndex()
    await vector_index.ensure_collection("embeddings", 16)
    await vector_index.upsert(
        "embeddings",
        "emb_chunk_1_embedding_v1",
        [0.1] * 16,
        {"source_chunk_id": "chunk_1"},
    )
    service = LifecycleService(InMemoryLifecycleRepository())
    executor = RepositoryLifecycleDeletionExecutor(
        raw_events=graph.raw_events,
        source_objects=graph.source_objects,
        source_files=graph.source_files,
        source_chunks=graph.source_chunks,
        embeddings=graph.embeddings,
        index_jobs=graph.index_jobs,
        payload_store=graph.payload_store,
        vector_deleter=InMemoryVectorLifecycleDeleter(vector_index.points),
    )

    tombstone = await service.execute_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_1",
        requested_by_user_id="usr_1",
        reason="customer_request",
        executor=executor,
    )

    assert tombstone.status == LifecycleActionStatus.COMPLETED
    assert tombstone.metadata_json["deleted_counts_json"] == {
        "raw_events": 1,
        "source_objects": 1,
        "source_files": 1,
        "source_chunks": 1,
        "embeddings": 1,
        "index_jobs": 1,
        "vector_points": 1,
        "payload_refs_deleted": 2,
        "payload_refs_skipped": 0,
        "expected_raw_events": 1,
        "expected_source_objects": 1,
        "expected_source_files": 1,
        "expected_source_chunks": 1,
        "expected_embeddings": 1,
        "expected_index_jobs": 1,
        "expected_vector_points": 1,
        "expected_payload_refs": 2,
    }
    assert graph.raw_events.get_by_id("raw_1").status == "deleted"
    assert graph.source_objects.get_by_id("so_1").status == "deleted"
    assert graph.source_files.get_by_id("file_1").status == "deleted"
    assert graph.source_chunks.get_by_id("chunk_1").status == "deleted"
    assert graph.embeddings.get_by_id("emb_chunk_1_embedding_v1").status == "stale"
    assert (
        graph.index_jobs.get_by_id(
            "idx_qdrant_source_chunk_chunk_1_upsert_index_v1"
        ).status
        == "stale"
    )
    assert vector_index.points["embeddings"] == {}
    for payload_ref in graph.payload_refs:
        with pytest.raises(PayloadNotFoundError):
            graph.payload_store.get(payload_ref)


@pytest.mark.asyncio
async def test_deletion_executor_deletes_object_and_file_level_chunks() -> None:
    graph = _seed_lifecycle_graph(include_object_level_chunk=True)
    service = LifecycleService(InMemoryLifecycleRepository())
    executor = RepositoryLifecycleDeletionExecutor(
        raw_events=graph.raw_events,
        source_objects=graph.source_objects,
        source_files=graph.source_files,
        source_chunks=graph.source_chunks,
        embeddings=graph.embeddings,
        index_jobs=graph.index_jobs,
        payload_store=graph.payload_store,
        vector_deleter=InMemoryVectorLifecycleDeleter(
            {"embeddings": {"emb_chunk_1_embedding_v1": object()}}
        ),
    )

    tombstone = await service.execute_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_1",
        requested_by_user_id="usr_1",
        reason="customer_request",
        executor=executor,
    )

    assert tombstone.status == LifecycleActionStatus.COMPLETED
    assert graph.source_chunks.get_by_id("chunk_1").status == "deleted"
    assert graph.source_chunks.get_by_id("chunk_object_1").status == "deleted"
    assert tombstone.metadata_json["deleted_counts_json"]["source_chunks"] == 2
    assert tombstone.metadata_json["deleted_counts_json"]["expected_source_chunks"] == 2


@pytest.mark.asyncio
async def test_repository_deletion_fails_tombstone_on_vector_mismatch() -> None:
    graph = _seed_lifecycle_graph()
    service = LifecycleService(InMemoryLifecycleRepository())
    executor = RepositoryLifecycleDeletionExecutor(
        raw_events=graph.raw_events,
        source_objects=graph.source_objects,
        source_files=graph.source_files,
        source_chunks=graph.source_chunks,
        embeddings=graph.embeddings,
        index_jobs=graph.index_jobs,
        payload_store=graph.payload_store,
        vector_deleter=InMemoryVectorLifecycleDeleter({"embeddings": {}}),
    )

    tombstone = await service.execute_deletion(
        workspace_id="ws_1",
        target_type="source_connection",
        target_id="src_1",
        requested_by_user_id="usr_1",
        reason="customer_request",
        executor=executor,
    )

    assert tombstone.status == LifecycleActionStatus.FAILED
    assert tombstone.metadata_json["error_code"] == "cleanup_mismatch"
    assert tombstone.metadata_json["mismatches_json"]["vector_points"] == {
        "expected": 1,
        "actual": 0,
    }


@pytest.mark.asyncio
async def test_repository_export_executor_writes_manifest_and_records() -> None:
    graph = _seed_lifecycle_graph()
    export_store = InMemoryPayloadStore()
    service = LifecycleService(InMemoryLifecycleRepository())
    executor = RepositoryLifecycleExportExecutor(
        export_store=export_store,
        raw_events=graph.raw_events,
        source_objects=graph.source_objects,
        source_files=graph.source_files,
        source_chunks=graph.source_chunks,
        embeddings=graph.embeddings,
        index_jobs=graph.index_jobs,
    )

    job = await service.execute_export(
        workspace_id="ws_1",
        requested_by_user_id="usr_1",
        export_scope="workspace",
        executor=executor,
    )
    exported = json.loads(export_store.get(job.destination_ref).decode())

    assert job.status == LifecycleActionStatus.COMPLETED
    assert job.metadata_json["counts"] == {
        "raw_events": 1,
        "source_objects": 1,
        "source_files": 1,
        "source_chunks": 1,
        "embeddings": 1,
        "index_jobs": 1,
    }
    assert exported["manifest"]["payload_refs"] == sorted(graph.payload_refs)
    assert exported["records"]["source_chunks"][0]["text"] == "delete this text"


class LifecycleGraph:
    def __init__(self) -> None:
        self.payload_store = InMemoryPayloadStore()
        self.raw_events = InMemoryRawEventRepository()
        self.source_objects = InMemorySourceObjectRepository()
        self.source_files = InMemorySourceFileRepository()
        self.source_chunks = InMemorySourceChunkRepository()
        self.embeddings = InMemoryEmbeddingRecordRepository()
        self.index_jobs = InMemoryIndexJobRepository()
        self.payload_refs: list[str] = []


def _seed_lifecycle_graph(
    *,
    include_object_level_chunk: bool = False,
) -> LifecycleGraph:
    graph = LifecycleGraph()
    now = datetime.now(UTC)
    raw_payload = graph.payload_store.put_json({"event": "raw"})
    file_payload = graph.payload_store.put_json({"file": "bytes"})
    graph.payload_refs = [raw_payload.payload_ref, file_payload.payload_ref]
    graph.raw_events.create_or_get_by_idempotency_key(
        item=RawEventInput(
            workspace_id="ws_1",
            source_connection_id="src_1",
            provider="fixture",
            external_event_id="evt_1",
            event_type="fixture.created",
            external_object_key="fixture:so_1",
            idempotency_key="evt_1",
            payload={"event": "raw"},
            raw_event_id="raw_1",
        ),
        payload_ref=raw_payload.payload_ref,
        payload_hash=raw_payload.payload_hash,
        payload_size_bytes=raw_payload.payload_size_bytes,
    )
    graph.source_objects.upsert_many(
        [
            SourceObject(
                id="so_1",
                workspace_id="ws_1",
                source_connection_id="src_1",
                provider="fixture",
                object_type="fixture_doc",
                external_object_id="so_1",
                external_object_key="fixture:so_1",
                content_hash="sha256:object",
                status=SourceObjectStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        ]
    )
    graph.source_files.upsert_many(
        [
            SourceFile(
                id="file_1",
                workspace_id="ws_1",
                source_object_id="so_1",
                source_connection_id="src_1",
                provider="fixture",
                external_file_id="file_1",
                external_object_key="fixture:file_1",
                storage_ref=file_payload.payload_ref,
                content_hash="sha256:file",
                status=SourceObjectStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        ]
    )
    chunks = [
        SourceChunk(
            id="chunk_1",
            workspace_id="ws_1",
            source_object_id="so_1",
            source_file_id="file_1",
            chunk_type="fixture",
            chunk_index=0,
            text="delete this text",
            text_hash="sha256:chunk",
            chunking_version="chunking-v1",
            status=SourceChunkStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    ]
    if include_object_level_chunk:
        chunks.append(
            SourceChunk(
                id="chunk_object_1",
                workspace_id="ws_1",
                source_object_id="so_1",
                source_file_id=None,
                chunk_type="fixture",
                chunk_index=1,
                text="delete this object text",
                text_hash="sha256:chunk-object",
                chunking_version="chunking-v1",
                status=SourceChunkStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
    graph.source_chunks.upsert_many(chunks)
    queued = graph.embeddings.queue_for_chunk(
        workspace_id="ws_1",
        source_chunk_id="chunk_1",
        provider="deterministic",
        model="deterministic",
        dimensions=16,
        task_type="retrieval_document",
        embedding_version="embedding-v1",
        chunking_version="chunking-v1",
        input_text_hash="sha256:chunk",
    )
    graph.embeddings.mark_completed(
        queued.record.id,
        vector_hash="sha256:vector",
        collection="embeddings",
    )
    graph.index_jobs.enqueue(
        workspace_id="ws_1",
        target_store="qdrant",
        target_type="source_chunk",
        target_id="chunk_1",
        operation="upsert",
        index_version="index-v1",
    )
    return graph
