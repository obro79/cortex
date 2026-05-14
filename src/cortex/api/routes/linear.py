from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from cortex.auth.dependencies import (
    enforce_plan_limit,
    require_permission,
    require_tenant_context,
)
from cortex.billing import UsageDimension
from cortex.connectors.linear.service import LinearConnectorServices
from cortex.tenancy import TenantContext
from cortex.tenancy.rbac import Permission

router = APIRouter(prefix="/connectors/linear", tags=["linear"])
TENANT_CONTEXT_DEPENDENCY = Depends(require_tenant_context)


def get_linear_services(request: Request) -> LinearConnectorServices:
    services = getattr(request.app.state, "linear_connector", None)
    if not isinstance(services, LinearConnectorServices):
        raise HTTPException(status_code=404, detail="linear connector is disabled")
    return services


@router.post("/install/api-token")
async def install_api_token(
    request: Request,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    token = str(body.get("api_token", ""))
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.CONNECTOR_SETUP,
    )
    return get_linear_services(request).install_api_token(
        workspace_id=workspace_id,
        token=token,
    )


@router.post("/sources/select")
async def select_sources(
    request: Request,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    sources = body.get("sources", [])
    if not workspace_id or not isinstance(sources, list):
        raise HTTPException(status_code=422, detail="invalid source selection")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SOURCE_SELECT,
    )
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.SOURCES,
        requested_quantity=len(sources),
    )
    return get_linear_services(request).select_sources(
        workspace_id=workspace_id,
        sources=[dict(source) for source in sources],
    )


@router.post("/backfill/{source_connection_id}")
async def backfill(
    request: Request,
    source_connection_id: str,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    issues = body.get("issues", [])
    if not workspace_id or not isinstance(issues, list):
        raise HTTPException(status_code=422, detail="workspace_id and issues required")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.CONNECTOR_SETUP,
    )
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.INDEXED_OBJECTS,
        requested_quantity=len(issues),
    )
    return await get_linear_services(request).backfill(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        issues=[dict(issue) for issue in issues],
    )


@router.post("/backfill-live/{source_connection_id}")
async def backfill_live(
    request: Request,
    source_connection_id: str,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.CONNECTOR_SETUP,
    )
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.INDEXED_OBJECTS,
        requested_quantity=int(body.get("limit", 25)),
    )
    return await get_linear_services(request).live_backfill(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        limit=int(body.get("limit", 25)),
    )


@router.get("/health/{workspace_id}")
async def health(
    request: Request,
    workspace_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.RETRIEVAL_READ,
    )
    return get_linear_services(request).health(workspace_id)
