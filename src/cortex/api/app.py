from fastapi import FastAPI

from cortex.api.routes.dev import router as dev_router
from cortex.api.routes.health import router as health_router
from cortex.config import Settings, get_settings
from cortex.dev.workbench import DevWorkbenchService
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
    return app


app = create_app()
