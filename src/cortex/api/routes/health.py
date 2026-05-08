from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from cortex.deployment.config import validate_runtime_config

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    issues = validate_runtime_config(settings, role="api")
    status_code = 200 if not issues else 503
    payload = {
        "status": "ready" if not issues else "not_ready",
        "checks": {
            "runtime_config": "ok" if not issues else "failed",
        },
        "issues": [
            {
                "field": issue.field,
                "code": issue.code,
                "message": issue.message,
            }
            for issue in issues
        ],
    }
    return JSONResponse(payload, status_code=status_code)
