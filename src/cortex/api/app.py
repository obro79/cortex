from typing import Any

from fastapi import FastAPI

from cortex.api.routes.dev import router as dev_router
from cortex.api.routes.github import router as github_router
from cortex.api.routes.health import router as health_router
from cortex.api.routes.linear import router as linear_router
from cortex.api.routes.repo_docs import router as repo_docs_router
from cortex.api.routes.slack import router as slack_router
from cortex.config import Settings, get_settings
from cortex.connectors.github.service import GitHubConnectorServices
from cortex.connectors.linear.service import LinearConnectorServices
from cortex.connectors.repo_docs.service import RepoDocsConnectorServices
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.db.session import create_sessionmaker
from cortex.dev.workbench import DevWorkbenchService
from cortex.events.bus import EventBus, KafkaEventBus
from cortex.ingestion.durable import SessionRawEventIngestionService
from cortex.ingestion.payloads import FilePayloadStore, PayloadStore
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
    event_bus: EventBus | None = None
    payload_store: PayloadStore | None = None
    ingestion_service: Any | None = None
    auto_drain_pipeline = True
    if resolved.cortex_event_bus == "kafka":
        if resolved.cortex_state_backend != "sql":
            raise ValueError("CORTEX_EVENT_BUS=kafka requires CORTEX_STATE_BACKEND=sql")
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
    if resolved.cortex_slack_connector_enabled:
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
    if resolved.cortex_linear_connector_enabled:
        linear_kwargs: dict[str, Any] = {}
        if event_bus is not None:
            linear_kwargs["event_bus"] = event_bus
        if payload_store is not None:
            linear_kwargs["payload_store"] = payload_store
        if ingestion_service is not None:
            linear_kwargs["ingestion"] = ingestion_service
        app.state.linear_connector = LinearConnectorServices(
            api_token_configured=bool(resolved.linear_api_token),
            **linear_kwargs,
        )
        app.include_router(linear_router)
    if resolved.cortex_github_connector_enabled:
        github_kwargs: dict[str, Any] = {}
        if event_bus is not None:
            github_kwargs["event_bus"] = event_bus
        if payload_store is not None:
            github_kwargs["payload_store"] = payload_store
        if ingestion_service is not None:
            github_kwargs["ingestion"] = ingestion_service
        app.state.github_connector = GitHubConnectorServices(
            app_configured=bool(resolved.github_app_id and resolved.github_private_key),
            webhook_secret=resolved.github_webhook_secret,
            **github_kwargs,
        )
        app.include_router(github_router)
    if resolved.cortex_repo_docs_connector_enabled:
        repo_docs_kwargs: dict[str, Any] = {}
        if event_bus is not None:
            repo_docs_kwargs["event_bus"] = event_bus
        if payload_store is not None:
            repo_docs_kwargs["payload_store"] = payload_store
        if ingestion_service is not None:
            repo_docs_kwargs["ingestion"] = ingestion_service
        app.state.repo_docs_connector = RepoDocsConnectorServices(**repo_docs_kwargs)
        app.include_router(repo_docs_router)
    return app


app = create_app()
