from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from cortex.auth.dependencies import (
    enforce_plan_limit,
    require_permission,
    require_tenant_context,
)
from cortex.billing import UsageDimension
from cortex.connectors.github.service import GitHubConnectorServices
from cortex.tenancy import TenantContext
from cortex.tenancy.rbac import Permission

router = APIRouter(prefix="/connectors/github", tags=["github"])
TENANT_CONTEXT_DEPENDENCY = Depends(require_tenant_context)


def get_github_services(request: Request) -> GitHubConnectorServices:
    services = getattr(request.app.state, "github_connector", None)
    if not isinstance(services, GitHubConnectorServices):
        raise HTTPException(status_code=404, detail="github connector is disabled")
    return services


@router.post("/install/app")
async def install_app(
    request: Request,
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
    return get_github_services(request).install_app(
        workspace_id=workspace_id,
        app_id=str(body.get("app_id", "")),
        private_key=str(body.get("private_key", "")),
    )


@router.post("/sources/select")
async def select_repos(
    request: Request,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    repos = body.get("repos", [])
    if not workspace_id or not isinstance(repos, list):
        raise HTTPException(status_code=422, detail="invalid repo selection")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SOURCE_SELECT,
    )
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.SOURCES,
        requested_quantity=len(repos),
    )
    return get_github_services(request).select_repos(
        workspace_id=workspace_id,
        repos=[dict(repo) for repo in repos],
    )


@router.post("/backfill/{source_connection_id}")
async def backfill(
    request: Request,
    source_connection_id: str,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    events = body.get("events", [])
    if not workspace_id or not isinstance(events, list):
        raise HTTPException(status_code=422, detail="workspace_id and events required")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.CONNECTOR_SETUP,
    )
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.INDEXED_OBJECTS,
        requested_quantity=len(events),
    )
    return await get_github_services(request).backfill(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        events=[dict(event) for event in events],
    )


@router.post("/backfill-live/{source_connection_id}")
async def backfill_live(
    request: Request,
    source_connection_id: str,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    owner = str(body.get("owner", ""))
    repo = str(body.get("repo", ""))
    if not workspace_id or not owner or not repo:
        raise HTTPException(
            status_code=422, detail="workspace_id, owner, repo required"
        )
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
    return await get_github_services(request).live_backfill(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        owner=owner,
        repo=repo,
        limit=int(body.get("limit", 25)),
    )


@router.post("/events")
async def github_events(
    request: Request,
    workspace_id: str,
    source_connection_id: str,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default="event"),
    x_github_delivery: str = Header(default=""),
) -> dict[str, object]:
    result = await get_github_services(request).webhook(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        body=await request.body(),
        signature=x_hub_signature_256,
        event_name=x_github_event,
        delivery_id=x_github_delivery or "delivery",
    )
    if result.get("ok") is not True:
        raise HTTPException(status_code=401, detail=result)
    return result


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
    return get_github_services(request).health(workspace_id)
