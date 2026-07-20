from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from cortex.api.rate_limit import install_api_rate_limit
from cortex.api.routes.billing import router as billing_router
from cortex.api.routes.case_study import router as case_study_router
from cortex.api.routes.context import router as context_router
from cortex.api.routes.demo import router as demo_router
from cortex.api.routes.dev import router as dev_router
from cortex.api.routes.github import router as github_router
from cortex.api.routes.health import router as health_router
from cortex.api.routes.lifecycle import router as lifecycle_router
from cortex.api.routes.linear import router as linear_router
from cortex.api.routes.repo_docs import router as repo_docs_router
from cortex.api.routes.slack import router as slack_router
from cortex.api.routes.ui import router as ui_router
from cortex.billing import (
    AsyncPlanEnforcementService,
    HttpStripeGateway,
    InMemoryBillingRepository,
    PlanEnforcementService,
    SqlAlchemyBillingRepository,
    StripeBillingService,
)
from cortex.config import Settings, get_settings
from cortex.connectors.github.client import RealGitHubClient
from cortex.connectors.github.service import GitHubConnectorServices
from cortex.connectors.linear.client import RealLinearClient
from cortex.connectors.linear.service import LinearConnectorServices
from cortex.connectors.repo_docs.service import RepoDocsConnectorServices
from cortex.connectors.slack.service import create_slack_connector_services
from cortex.db.session import create_sessionmaker
from cortex.dev.workbench import DevWorkbenchService
from cortex.events.bus import EventBus, KafkaEventBus
from cortex.ingestion.durable import SessionRawEventIngestionService
from cortex.ingestion.payloads import FilePayloadStore, PayloadStore
from cortex.lifecycle import InMemoryLifecycleRepository
from cortex.observability.logging import setup_logging
from cortex.observability.tracing import init_tracing
from cortex.permissions import InMemoryProviderPrincipalMappingRepository
from cortex.permissions.service import PermissionService
from cortex.platform import EphemeralCacheService, build_ephemeral_cache
from cortex.platform.rate_limits import RateLimitPolicy, RateLimitService
from cortex.runtime import CortexRuntime, DurableContextRetrieval
from cortex.security.audit import InMemoryAuditLogRepository
from cortex.tenancy import InMemoryTenantRepository, SqlAlchemyTenantRepository
from cortex.ui.source_health import SourceHealthViewService


def create_app(
    settings: Settings | None = None,
    *,
    ephemeral_cache: EphemeralCacheService | None = None,
    cortex_runtime: CortexRuntime | None = None,
    durable_permission_service_factory: Callable[[AsyncSession], PermissionService]
    | None = None,
) -> FastAPI:
    resolved = settings or get_settings()
    setup_logging(resolved.cortex_log_level)
    init_tracing("cortex-api")

    app = FastAPI(title="Cortex API", version="0.1.0")
    app.state.settings = resolved
    if cortex_runtime is not None:
        app.state.cortex_runtime = cortex_runtime
    session_factory = (
        create_sessionmaker(resolved.database_url)
        if resolved.cortex_state_backend == "sql"
        else None
    )
    app.state.session_factory = session_factory
    if (
        cortex_runtime is None
        and session_factory is not None
        and resolved.qdrant_url
        and durable_permission_service_factory is not None
    ):
        # SQL is canonical and Qdrant only supplies derived vector candidates.
        # A durable permission snapshot factory is mandatory: installing a
        # retrieval runtime without it would either leak unscoped content or
        # fail every request at execution time.  Deployments that have not
        # wired durable scope/ACL authority receive an explicit 503 instead.
        app.state.cortex_runtime = CortexRuntime(
            retrieval=DurableContextRetrieval(
                session_factory=session_factory,
                settings=resolved,
                permission_service_factory=durable_permission_service_factory,
            ),
            context_gate=None,
            live_data=True,
        )
    app.state.lifecycle_repository = InMemoryLifecycleRepository()
    app.state.provider_principal_mapping_repository = (
        InMemoryProviderPrincipalMappingRepository()
    )
    if session_factory is not None:
        app.state.billing_repository = SqlAlchemyBillingRepository(session_factory)
        app.state.plan_enforcement = AsyncPlanEnforcementService(
            app.state.billing_repository
        )
    else:
        app.state.billing_repository = InMemoryBillingRepository()
        app.state.plan_enforcement = PlanEnforcementService(
            app.state.billing_repository
        )
    if resolved.stripe_webhook_secret:
        app.state.stripe_billing_service = StripeBillingService(
            repository=app.state.billing_repository,
            gateway=HttpStripeGateway(api_key=resolved.stripe_api_key),
            webhook_secret=resolved.stripe_webhook_secret,
        )
    if resolved.cortex_public_auth_enabled:
        app.state.tenant_repository = (
            SqlAlchemyTenantRepository(session_factory)
            if session_factory is not None
            else InMemoryTenantRepository()
        )
    cache = ephemeral_cache
    if cache is None and (
        resolved.cortex_api_rate_limit_enabled
        or resolved.cortex_provider_rate_limit_enabled
    ):
        cache = build_ephemeral_cache(resolved)
    if resolved.cortex_api_rate_limit_enabled:
        if cache is None:
            raise RuntimeError("API rate limiting requires an ephemeral cache")
        app.state.ephemeral_cache = cache
        install_api_rate_limit(
            app,
            cache=cache,
            policy=RateLimitPolicy(
                name="api",
                limit=resolved.cortex_api_rate_limit_requests,
                window_seconds=resolved.cortex_api_rate_limit_window_seconds,
                namespace="http",
            ),
        )
    provider_rate_limiter = (
        RateLimitService(cache)
        if (cache is not None and resolved.cortex_provider_rate_limit_enabled)
        else None
    )
    provider_rate_limit_policy = (
        RateLimitPolicy(
            name="provider",
            limit=resolved.cortex_provider_rate_limit_requests,
            window_seconds=resolved.cortex_provider_rate_limit_window_seconds,
            namespace="provider",
        )
        if resolved.cortex_provider_rate_limit_enabled
        else None
    )
    app.include_router(health_router)
    app.include_router(case_study_router)
    app.include_router(billing_router)
    app.include_router(lifecycle_router)
    # This boundary intentionally has no in-memory fallback: deployers inject a
    # durable retrieval runtime, and disabled public auth remains explicit.
    app.include_router(context_router)
    if resolved.cortex_dev_workbench_enabled and resolved.cortex_env not in {
        "local",
        "test",
    }:
        raise ValueError("dev workbench cannot be enabled outside local/test")
    if resolved.cortex_dev_workbench_enabled:
        app.state.dev_workbench = DevWorkbenchService()
        app.include_router(dev_router)
        app.include_router(demo_router)
    if resolved.cortex_ui_enabled:
        app.state.audit_log = InMemoryAuditLogRepository()
    event_bus: EventBus | None = None
    payload_store: PayloadStore | None = None
    ingestion_service: Any | None = None
    auto_drain_pipeline = True
    if resolved.cortex_event_bus == "kafka":
        if resolved.cortex_state_backend != "sql":
            raise ValueError("CORTEX_EVENT_BUS=kafka requires CORTEX_STATE_BACKEND=sql")
        if session_factory is None:
            raise ValueError("CORTEX_STATE_BACKEND=sql requires a session factory")
        event_bus = KafkaEventBus(
            bootstrap_servers=resolved.kafka_bootstrap_servers,
        )
        payload_store = FilePayloadStore(
            resolved.payload_store_path or "/var/lib/cortex/payloads"
        )
        ingestion_service = SessionRawEventIngestionService(
            session_factory=session_factory,
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
            provider_rate_limiter=provider_rate_limiter,
            provider_rate_limit_policy=provider_rate_limit_policy,
            settings=resolved,
            session_factory=(
                session_factory if resolved.cortex_state_backend == "sql" else None
            ),
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
            api_token=resolved.linear_api_token,
            client=RealLinearClient(),
            provider_rate_limiter=provider_rate_limiter,
            provider_rate_limit_policy=provider_rate_limit_policy,
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
            app_configured=bool(
                (resolved.github_app_id and resolved.github_private_key)
                or resolved.github_installation_token
            ),
            installation_token=resolved.github_installation_token,
            installation_workspace_id=resolved.github_installation_workspace_id,
            client=RealGitHubClient(),
            webhook_secret=resolved.github_webhook_secret,
            provider_rate_limiter=provider_rate_limiter,
            provider_rate_limit_policy=provider_rate_limit_policy,
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
    if resolved.cortex_ui_enabled:
        app.state.source_health_view = SourceHealthViewService(
            slack_connector=getattr(app.state, "slack_connector", None)
        )
        app.include_router(ui_router)
    return app


app = create_app(
    Settings.model_construct(
        cortex_event_bus="memory",
        cortex_state_backend="memory",
        cortex_slack_connector_enabled=False,
    )
)
