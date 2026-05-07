from __future__ import annotations

from dataclasses import dataclass

from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository
from cortex.ingestion.service import RawEventIngestionService

from .backfill import SlackBackfillService
from .client import EmptySlackWebClient, SlackWebClient
from .health import SlackHealthService
from .oauth import SlackOAuthService
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
    event_bus: InMemoryEventBus


def create_slack_connector_services(
    *,
    signing_secret: str = "local-signing-secret",
    slack_client: SlackWebClient | None = None,
) -> SlackConnectorServices:
    secrets = InMemorySecretRefRepository()
    installations = InMemoryOAuthInstallationRepository()
    source_connections = InMemorySourceConnectionRepository()
    deliveries = InMemoryWebhookDeliveryRepository()
    cursors = InMemoryProviderCursorRepository()
    backfills = InMemoryBackfillJobRepository()
    event_bus = InMemoryEventBus()
    raw_events = InMemoryRawEventRepository()
    ingestion = RawEventIngestionService(
        repository=raw_events,
        payload_store=InMemoryPayloadStore(),
        publisher=RawEventPublisher(event_bus),
    )
    return SlackConnectorServices(
        oauth=SlackOAuthService(secrets=secrets, installations=installations),
        sources=SlackSourceSelectionService(
            installations=installations,
            source_connections=source_connections,
        ),
        webhooks=SlackWebhookService(
            deliveries=deliveries,
            source_connections=source_connections,
            ingestion=ingestion,
            verifier=SlackWebhookVerifier(signing_secret),
        ),
        backfill=SlackBackfillService(
            client=slack_client or EmptySlackWebClient(),
            source_connections=source_connections,
            cursors=cursors,
            backfills=backfills,
            ingestion=ingestion,
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
        event_bus=event_bus,
    )
