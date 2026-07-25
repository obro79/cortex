from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from cortex.chunking.repositories import SqlAlchemySourceChunkRepository
from cortex.config import Settings
from cortex.embeddings.repositories import SqlAlchemyEmbeddingRecordRepository
from cortex.indexing.repositories import SqlAlchemyIndexJobRepository
from cortex.ingestion.payloads import FilePayloadStore
from cortex.ingestion.raw_events import SqlAlchemyRawEventRepository
from cortex.lifecycle.executors import (
    QdrantLifecycleDeleter,
    RepositoryLifecycleDeletionExecutor,
    RepositoryLifecycleExportExecutor,
)
from cortex.normalization.repositories import (
    SqlAlchemySourceFileRepository,
    SqlAlchemySourceObjectRepository,
)


def create_sql_deletion_executor(
    *,
    session: AsyncSession,
    settings: Settings,
) -> RepositoryLifecycleDeletionExecutor:
    vector_deleter = (
        QdrantLifecycleDeleter(
            base_url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
        if settings.qdrant_url
        else None
    )
    return RepositoryLifecycleDeletionExecutor(
        raw_events=SqlAlchemyRawEventRepository(session),
        source_objects=SqlAlchemySourceObjectRepository(session),
        source_files=SqlAlchemySourceFileRepository(session),
        source_chunks=SqlAlchemySourceChunkRepository(session),
        embeddings=SqlAlchemyEmbeddingRecordRepository(session),
        index_jobs=SqlAlchemyIndexJobRepository(session),
        payload_store=FilePayloadStore(_payload_store_path(settings)),
        vector_deleter=vector_deleter,
    )


def create_sql_export_executor(
    *,
    session: AsyncSession,
    settings: Settings,
) -> RepositoryLifecycleExportExecutor:
    return RepositoryLifecycleExportExecutor(
        export_store=FilePayloadStore(_payload_store_path(settings)),
        raw_events=SqlAlchemyRawEventRepository(session),
        source_objects=SqlAlchemySourceObjectRepository(session),
        source_files=SqlAlchemySourceFileRepository(session),
        source_chunks=SqlAlchemySourceChunkRepository(session),
        embeddings=SqlAlchemyEmbeddingRecordRepository(session),
        index_jobs=SqlAlchemyIndexJobRepository(session),
    )


def _payload_store_path(settings: Settings) -> str:
    return settings.payload_store_path or "/var/lib/cortex/payloads"
