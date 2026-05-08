from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.publishers import SourceChunkPublisher
from cortex.chunking.repositories import SqlAlchemySourceChunkRepository
from cortex.chunking.service import ChunkingService
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.config import Settings
from cortex.contracts.pipeline_events import PipelineEventEnvelope
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.embeddings.publishers import EmbeddingPublisher
from cortex.embeddings.repositories import SqlAlchemyEmbeddingRecordRepository
from cortex.embeddings.service import EmbeddingService
from cortex.events.bus import PIPELINE_TOPICS, KafkaEventBus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import FilePayloadStore
from cortex.ingestion.raw_events import SqlAlchemyRawEventRepository
from cortex.normalization.publishers import SourceFilePublisher, SourceObjectPublisher
from cortex.normalization.repositories import (
    SqlAlchemyRelationshipSeedRepository,
    SqlAlchemySourceFileRepository,
    SqlAlchemySourceObjectRepository,
)
from cortex.normalization.service import SourceNormalizationService
from cortex.platform import build_ephemeral_cache
from cortex.platform.rate_limits import RateLimitPolicy, RateLimitService
from cortex.workers.embeddings import EmbeddingWorkerSkeleton
from cortex.workers.kafka import KafkaPipelineConsumer, RetryablePipelineError


@dataclass(frozen=True)
class DurablePipelineSettings:
    bootstrap_servers: str
    group_id: str
    database_url: str
    payload_store_path: str


class SqlPipelineDispatcher:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        payload_store: FilePayloadStore,
        event_bus: KafkaEventBus,
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.payload_store = payload_store
        self.event_bus = event_bus
        self.settings = settings
        self.retrieval_config = load_retrieval_config()
        self.cache = (
            build_ephemeral_cache(settings)
            if settings.cortex_model_rate_limit_enabled
            else None
        )

    async def aclose(self) -> None:
        await self.event_bus.stop()

    async def drain(self, event_bus: InMemoryEventBus) -> object:
        processed = 0
        for envelope in event_bus.events:
            buffered_events = InMemoryEventBus()
            result: object | None = None
            async with self.session_factory() as session:
                try:
                    result = await self._dispatch(session, envelope, buffered_events)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
            if _result_status(result) == "retryable":
                raise RetryablePipelineError(f"retryable handler result: {result!r}")
            for buffered_event in buffered_events.events:
                try:
                    await self.event_bus.publish(buffered_event)
                except Exception as error:
                    raise RetryablePipelineError(
                        f"downstream publish failed: {type(error).__name__}"
                    ) from error
            processed += 1
        return {"processed_event_count": processed}

    async def _dispatch(
        self,
        session: AsyncSession,
        envelope: PipelineEventEnvelope,
        event_bus: InMemoryEventBus,
    ) -> object | None:
        source_objects = SqlAlchemySourceObjectRepository(session)
        source_files = SqlAlchemySourceFileRepository(session)
        source_chunks = SqlAlchemySourceChunkRepository(session)
        normalization = SourceNormalizationService(
            raw_events=SqlAlchemyRawEventRepository(session),
            payload_store=self.payload_store,
            source_objects=source_objects,
            source_files=source_files,
            relationship_seeds=SqlAlchemyRelationshipSeedRepository(session),
            source_object_publisher=SourceObjectPublisher(event_bus),
            source_file_publisher=SourceFilePublisher(event_bus),
        )
        chunking = ChunkingService(
            source_objects=source_objects,
            source_files=source_files,
            source_chunks=source_chunks,
            chunker=SourceAwareChunker(self.retrieval_config.chunking),
            publisher=SourceChunkPublisher(event_bus),
        )
        embedding_service = EmbeddingService(
            source_chunks=source_chunks,
            embeddings=SqlAlchemyEmbeddingRecordRepository(session),
            provider=DeterministicEmbeddingProvider(
                dimensions=16,
                version=self.retrieval_config.embeddings.version,
            ),
            publisher=EmbeddingPublisher(event_bus),
            model_rate_limiter=(
                RateLimitService(self.cache)
                if self.cache is not None
                and self.settings.cortex_model_rate_limit_enabled
                else None
            ),
            model_rate_limit_policy=(
                RateLimitPolicy(
                    name="embedding",
                    limit=self.settings.cortex_model_rate_limit_requests,
                    window_seconds=(
                        self.settings.cortex_model_rate_limit_window_seconds
                    ),
                    namespace="model",
                )
                if self.settings.cortex_model_rate_limit_enabled
                else None
            ),
        )
        embeddings = EmbeddingWorkerSkeleton(embedding_service)
        if envelope.event_type == "raw_event.persisted":
            return await normalization.handle_raw_event_persisted(envelope)
        elif envelope.event_type == "source_object.upserted":
            return await chunking.handle_source_object_upserted(envelope)
        elif envelope.event_type == "source_file.fetched":
            return await chunking.handle_source_file_fetched(envelope)
        elif envelope.event_type == "source_chunk.upserted":
            return await embeddings.handle_source_chunk_upserted(envelope)
        elif envelope.event_type == "embedding.requested":
            return await embeddings.handle_embedding_requested(envelope)
        return None


def _result_status(result: object | None) -> str | None:
    if result is None:
        return None
    if isinstance(result, dict):
        value = result.get("status")
        return str(value) if value is not None else None
    value = getattr(result, "status", None)
    return str(value) if value is not None else None


def durable_pipeline_settings(settings: Settings) -> DurablePipelineSettings:
    if settings.cortex_event_bus != "kafka":
        raise ValueError("CORTEX_EVENT_BUS=kafka is required for the pipeline worker")
    if settings.cortex_state_backend != "sql":
        raise ValueError("CORTEX_STATE_BACKEND=sql is required for Kafka pipeline")
    if not settings.kafka_bootstrap_servers:
        raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required")
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required")
    return DurablePipelineSettings(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        database_url=settings.database_url,
        payload_store_path=settings.payload_store_path or "/var/lib/cortex/payloads",
    )


def create_kafka_pipeline_consumer(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> KafkaPipelineConsumer:
    resolved = durable_pipeline_settings(settings)
    event_bus = KafkaEventBus(bootstrap_servers=resolved.bootstrap_servers)
    dispatcher = SqlPipelineDispatcher(
        session_factory=session_factory,
        payload_store=FilePayloadStore(resolved.payload_store_path),
        event_bus=event_bus,
        settings=settings,
    )
    return KafkaPipelineConsumer(
        bootstrap_servers=resolved.bootstrap_servers,
        group_id=resolved.group_id,
        dispatcher=dispatcher,
    )


def pipeline_topics() -> tuple[str, ...]:
    return PIPELINE_TOPICS
