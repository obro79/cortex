from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from cortex.auth.dependencies import (
    enforce_plan_limit,
    require_permission,
    require_tenant_context,
)
from cortex.billing import UsageDimension
from cortex.connectors.repo_docs.service import RepoDocsConnectorServices
from cortex.tenancy import TenantContext
from cortex.tenancy.rbac import Permission

router = APIRouter(prefix="/connectors/repo-docs", tags=["repo-docs"])
TENANT_CONTEXT_DEPENDENCY = Depends(require_tenant_context)


def get_repo_docs_services(request: Request) -> RepoDocsConnectorServices:
    services = getattr(request.app.state, "repo_docs_connector", None)
    if not isinstance(services, RepoDocsConnectorServices):
        raise HTTPException(status_code=404, detail="repo docs connector is disabled")
    return services


@router.post("/sources/select")
async def select_roots(
    request: Request,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    roots = body.get("roots", [])
    if not workspace_id or not isinstance(roots, list):
        raise HTTPException(status_code=422, detail="invalid docs root selection")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SOURCE_SELECT,
    )
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.SOURCES,
        requested_quantity=len(roots),
    )
    return get_repo_docs_services(request).select_roots(
        workspace_id=workspace_id,
        roots=[dict(root) for root in roots],
    )


@router.post("/import/{source_connection_id}")
async def import_docs(
    request: Request,
    source_connection_id: str,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    docs = body.get("docs", [])
    if not workspace_id or not isinstance(docs, list):
        raise HTTPException(status_code=422, detail="workspace_id and docs required")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.CONNECTOR_SETUP,
    )
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.INDEXED_OBJECTS,
        requested_quantity=len(docs),
    )
    return await get_repo_docs_services(request).import_docs(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        docs=[dict(doc) for doc in docs],
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
    return get_repo_docs_services(request).health(workspace_id)
