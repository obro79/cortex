from fastapi import FastAPI

from cortex.api.routes.dev import router as dev_router
from cortex.api.routes.health import router as health_router
from cortex.api.routes.slack import router as slack_router
from cortex.config import Settings, get_settings
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.db.session import create_sessionmaker
from cortex.dev.workbench import DevWorkbenchService
from cortex.events.bus import KafkaEventBus
from cortex.ingestion.durable import SessionRawEventIngestionService
from cortex.ingestion.payloads import FilePayloadStore
from cortex.observability.logging import setup_logging
from cortex.observability.tracing import init_tracing


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    setup_logging(resolved.cortex_log_level)
    init_tracing("cortex-api")

    app = FastAPI(title="Cortex API", version="0.1.0")
    app.state.settings = resolved
    app.include_router(health_router)
    if resolved.cortex_dev_workbench_enabled:
        app.state.dev_workbench = DevWorkbenchService()
        app.include_router(dev_router)
    if resolved.cortex_slack_connector_enabled:
        event_bus = None
        payload_store = None
        ingestion_service = None
        auto_drain_pipeline = True
        if resolved.cortex_event_bus == "kafka":
            if resolved.cortex_state_backend != "sql":
                raise ValueError(
                    "CORTEX_EVENT_BUS=kafka requires CORTEX_STATE_BACKEND=sql"
                )
            event_bus = KafkaEventBus(
                bootstrap_servers=resolved.kafka_bootstrap_servers,
            )
            payload_store = FilePayloadStore(
                resolved.payload_store_path or "/var/lib/cortex/payloads"
            )
            ingestion_service = SessionRawEventIngestionService(
                session_factory=create_sessionmaker(resolved.database_url),
                payload_store=payload_store,
                event_bus=event_bus,
            )
            auto_drain_pipeline = False
        app.state.slack_connector = create_slack_connector_services(
            signing_secret=resolved.slack_signing_secret or "local-signing-secret",
            client_id=resolved.slack_client_id,
            client_secret=resolved.slack_client_secret,
            redirect_uri=resolved.slack_redirect_uri,
            event_bus=event_bus,
            payload_store=payload_store,
            ingestion_service=ingestion_service,
            auto_drain_pipeline=auto_drain_pipeline,
        )
        app.include_router(slack_router)
    return app


app = create_app()
