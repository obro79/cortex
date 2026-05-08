from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from cortex.connectors.linear.service import LinearConnectorServices

router = APIRouter(prefix="/connectors/linear", tags=["linear"])


def get_linear_services(request: Request) -> LinearConnectorServices:
    services = getattr(request.app.state, "linear_connector", None)
    if not isinstance(services, LinearConnectorServices):
        raise HTTPException(status_code=404, detail="linear connector is disabled")
    return services


@router.post("/install/api-token")
async def install_api_token(
    request: Request, body: dict[str, Any]
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    token = str(body.get("api_token", ""))
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")
    return get_linear_services(request).install_api_token(
        workspace_id=workspace_id,
        token=token,
    )


@router.post("/sources/select")
async def select_sources(request: Request, body: dict[str, Any]) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    sources = body.get("sources", [])
    if not workspace_id or not isinstance(sources, list):
        raise HTTPException(status_code=422, detail="invalid source selection")
    return get_linear_services(request).select_sources(
        workspace_id=workspace_id,
        sources=[dict(source) for source in sources],
    )


@router.post("/backfill/{source_connection_id}")
async def backfill(
    request: Request, source_connection_id: str, body: dict[str, Any]
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    issues = body.get("issues", [])
    if not workspace_id or not isinstance(issues, list):
        raise HTTPException(status_code=422, detail="workspace_id and issues required")
    return await get_linear_services(request).backfill(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        issues=[dict(issue) for issue in issues],
    )


@router.get("/health/{workspace_id}")
async def health(request: Request, workspace_id: str) -> dict[str, object]:
    return get_linear_services(request).health(workspace_id)
