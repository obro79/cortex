from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cortex.chunking.config import load_retrieval_config
from cortex.chunking.publishers import SourceChunkPublisher
from cortex.chunking.repositories import InMemorySourceChunkRepository
from cortex.chunking.service import ChunkingService
from cortex.chunking.source_aware import SourceAwareChunker
from cortex.embeddings.deterministic import DeterministicEmbeddingProvider
from cortex.embeddings.publishers import EmbeddingPublisher
from cortex.embeddings.repositories import InMemoryEmbeddingRecordRepository
from cortex.embeddings.service import EmbeddingService
from cortex.events.bus import EventBus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import IngestionResult, RawEventIngestionService
from cortex.normalization.publishers import SourceFilePublisher, SourceObjectPublisher
from cortex.normalization.repositories import (
    InMemoryRelationshipSeedRepository,
    InMemorySourceFileRepository,
    InMemorySourceObjectRepository,
)
from cortex.normalization.service import SourceNormalizationService
from cortex.platform.rate_limits import RateLimitPolicy, RateLimitService
from cortex.workers.embeddings import EmbeddingWorkerSkeleton
from cortex.workers.pipeline import InMemoryPipelineDispatcher

from .backfill import SlackBackfillService
from .client import EmptySlackWebClient, RealSlackWebClient, SlackWebClient
from .health import SlackHealthService
from .oauth import RealSlackOAuthClient, SlackOAuthClient, SlackOAuthService
from .repositories import (
    InMemoryBackfillJobRepository,
    InMemoryOAuthInstallationRepository,
    InMemoryProviderCursorRepository,
    InMemorySecretRefRepository,
    InMemorySourceConnectionRepository,
    InMemoryWebhookDeliveryRepository,
)
from .sources import SlackSourceSelectionService
from .webhooks import SlackWebhookService, SlackWebhookVerifier


class SlackIngestionService(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


@dataclass(frozen=True)
class SlackConnectorServices:
    oauth: SlackOAuthService
    sources: SlackSourceSelectionService
    webhooks: SlackWebhookService
    backfill: SlackBackfillService
    health: SlackHealthService
    secrets: InMemorySecretRefRepository
    installations: InMemoryOAuthInstallationRepository
    source_connections: InMemorySourceConnectionRepository
    deliveries: InMemoryWebhookDeliveryRepository
    cursors: InMemoryProviderCursorRepository
    backfills: InMemoryBackfillJobRepository
    raw_events: InMemoryRawEventRepository
    payload_store: PayloadStore
    source_objects: InMemorySourceObjectRepository
    source_files: InMemorySourceFileRepository
    source_chunks: InMemorySourceChunkRepository
    embeddings: InMemoryEmbeddingRecordRepository
    pipeline: InMemoryPipelineDispatcher
    event_bus: EventBus
    auto_drain_pipeline: bool = True


def create_slack_connector_services(
    *,
    signing_secret: str = "local-signing-secret",
    client_id: str = "",
    client_secret: str = "",
    redirect_uri: str = "",
    oauth_client: SlackOAuthClient | None = None,
    slack_client: SlackWebClient | None = None,
    event_bus: EventBus | None = None,
    payload_store: PayloadStore | None = None,
    ingestion_service: SlackIngestionService | None = None,
    auto_drain_pipeline: bool = True,
    provider_rate_limiter: RateLimitService | None = None,
    provider_rate_limit_policy: RateLimitPolicy | None = None,
) -> SlackConnectorServices:
    secrets = InMemorySecretRefRepository()
    installations = InMemoryOAuthInstallationRepository()
    source_connections = InMemorySourceConnectionRepository()
    deliveries = InMemoryWebhookDeliveryRepository()
    cursors = InMemoryProviderCursorRepository()
    backfills = InMemoryBackfillJobRepository()
    resolved_event_bus = event_bus or InMemoryEventBus()
    raw_events = InMemoryRawEventRepository()
    resolved_payload_store = payload_store or InMemoryPayloadStore()
    source_objects = InMemorySourceObjectRepository()
    source_files = InMemorySourceFileRepository()
    source_chunks = InMemorySourceChunkRepository()
    embedding_records = InMemoryEmbeddingRecordRepository()
    retrieval_config = load_retrieval_config()
    ingestion = ingestion_service or RawEventIngestionService(
        repository=raw_events,
        payload_store=resolved_payload_store,
        publisher=RawEventPublisher(resolved_event_bus),
    )
    resolved_oauth_client = oauth_client
    if resolved_oauth_client is None and client_id and client_secret and redirect_uri:
        resolved_oauth_client = RealSlackOAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    resolved_slack_client = slack_client
    if resolved_slack_client is None and client_id and client_secret and redirect_uri:
        resolved_slack_client = RealSlackWebClient()
    normalization = SourceNormalizationService(
        raw_events=raw_events,
        payload_store=resolved_payload_store,
        source_objects=source_objects,
        source_files=source_files,
        relationship_seeds=InMemoryRelationshipSeedRepository(),
        source_object_publisher=SourceObjectPublisher(resolved_event_bus),
        source_file_publisher=SourceFilePublisher(resolved_event_bus),
    )
    chunking = ChunkingService(
        source_objects=source_objects,
        source_files=source_files,
        source_chunks=source_chunks,
        chunker=SourceAwareChunker(retrieval_config.chunking),
        publisher=SourceChunkPublisher(resolved_event_bus),
    )
    embedding_service = EmbeddingService(
        source_chunks=source_chunks,
        embeddings=embedding_records,
        provider=DeterministicEmbeddingProvider(
            dimensions=16,
            version=retrieval_config.embeddings.version,
        ),
        publisher=EmbeddingPublisher(resolved_event_bus),
    )
    pipeline = InMemoryPipelineDispatcher(
        normalization=normalization,
        chunking=chunking,
        embeddings=EmbeddingWorkerSkeleton(embedding_service),
    )
    return SlackConnectorServices(
        oauth=SlackOAuthService(
            secrets=secrets,
            installations=installations,
            client=resolved_oauth_client,
            client_id=client_id,
            redirect_uri=redirect_uri,
        ),
        sources=SlackSourceSelectionService(
            installations=installations,
            secrets=secrets,
            source_connections=source_connections,
            client=resolved_slack_client or EmptySlackWebClient(),
        ),
        webhooks=SlackWebhookService(
            deliveries=deliveries,
            source_connections=source_connections,
            ingestion=ingestion,
            verifier=SlackWebhookVerifier(signing_secret),
        ),
        backfill=SlackBackfillService(
            client=resolved_slack_client or EmptySlackWebClient(),
            source_connections=source_connections,
            installations=installations,
            secrets=secrets,
            cursors=cursors,
            backfills=backfills,
            ingestion=ingestion,
            provider_rate_limiter=provider_rate_limiter,
            provider_rate_limit_policy=provider_rate_limit_policy,
        ),
        health=SlackHealthService(
            installations=installations,
            source_connections=source_connections,
            cursors=cursors,
            backfills=backfills,
        ),
        secrets=secrets,
        installations=installations,
        source_connections=source_connections,
        deliveries=deliveries,
        cursors=cursors,
        backfills=backfills,
        raw_events=raw_events,
        payload_store=resolved_payload_store,
        source_objects=source_objects,
        source_files=source_files,
        source_chunks=source_chunks,
        embeddings=embedding_records,
        pipeline=pipeline,
        event_bus=resolved_event_bus,
        auto_drain_pipeline=auto_drain_pipeline,
    )
