from fastapi import APIRouter, Request

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, str | bool]:
    settings = request.app.state.settings
    return {
        "status": "ready",
        "database_configured": bool(settings.database_url),
    }
