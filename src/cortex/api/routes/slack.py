from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from cortex.auth.dependencies import (
    enforce_plan_limit,
    require_permission,
    require_tenant_context,
)
from cortex.billing import UsageDimension
from cortex.connectors.slack.service import SlackConnectorServices
from cortex.events.in_memory import InMemoryEventBus
from cortex.tenancy import TenantContext
from cortex.tenancy.rbac import Permission

router = APIRouter(prefix="/connectors/slack", tags=["slack"])
TENANT_CONTEXT_DEPENDENCY = Depends(require_tenant_context)


def get_slack_services(request: Request) -> SlackConnectorServices:
    services = getattr(request.app.state, "slack_connector", None)
    if not isinstance(services, SlackConnectorServices):
        raise HTTPException(status_code=404, detail="slack connector is disabled")
    return services


@router.post("/oauth/start")
async def start_oauth(
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
    return get_slack_services(request).oauth.start_install(
        workspace_id=workspace_id,
        actor_id=context.user_id,
    )


@router.get("/oauth/start")
async def redirect_oauth_start(
    request: Request,
    workspace_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> RedirectResponse:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.CONNECTOR_SETUP,
    )
    response = get_slack_services(request).oauth.start_install(
        workspace_id=workspace_id,
        actor_id=context.user_id,
    )
    authorization_url = response.get("authorization_url")
    if not isinstance(authorization_url, str) or not authorization_url:
        raise HTTPException(status_code=409, detail="slack oauth is not configured")
    return RedirectResponse(authorization_url)


@router.post("/oauth/complete")
async def complete_oauth(request: Request, body: dict[str, Any]) -> dict[str, object]:
    code = str(body.get("code", ""))
    state = str(body.get("state", ""))
    if not code or not state:
        raise HTTPException(status_code=422, detail="code and state are required")
    response = await get_slack_services(request).oauth.complete_install(
        code=code,
        state=state,
    )
    if not response["ok"]:
        raise HTTPException(status_code=409, detail=response)
    return response


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(default=""),
    state: str = Query(default=""),
) -> dict[str, object]:
    if not code or not state:
        raise HTTPException(status_code=422, detail="code and state are required")
    response = await get_slack_services(request).oauth.complete_install(
        code=code,
        state=state,
    )
    if not response["ok"]:
        raise HTTPException(status_code=409, detail=response)
    return response


@router.get("/sources/channels")
async def list_channels(
    request: Request,
    workspace_id: str,
    oauth_installation_id: str,
    cursor: str | None = None,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SOURCE_SELECT,
    )
    try:
        return await get_slack_services(request).sources.list_channels(
            workspace_id=workspace_id,
            oauth_installation_id=oauth_installation_id,
            cursor=cursor,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/sources/select")
async def select_sources(
    request: Request,
    body: dict[str, Any],
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    installation_id = str(body.get("oauth_installation_id", ""))
    channels = body.get("channels", [])
    if not workspace_id or not installation_id or not isinstance(channels, list):
        raise HTTPException(status_code=422, detail="invalid source selection")
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.SOURCE_SELECT,
    )
    try:
        await get_slack_services(request).sources.require_installation_workspace(
            workspace_id=workspace_id,
            oauth_installation_id=installation_id,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    await enforce_plan_limit(
        request,
        context,
        dimension=UsageDimension.SOURCES,
        requested_quantity=len(channels),
    )
    try:
        return await get_slack_services(request).sources.select_channels(
            workspace_id=workspace_id,
            oauth_installation_id=installation_id,
            channels=[dict(channel) for channel in channels],
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/events")
async def slack_events(
    request: Request,
    x_slack_request_timestamp: str = Header(default=""),
    x_slack_signature: str = Header(default=""),
    x_slack_retry_num: str | None = Header(default=None),
) -> dict[str, object]:
    workspace_id = request.query_params.get("workspace_id", "ws_1")
    body = await request.body()
    services = get_slack_services(request)
    result = await services.webhooks.handle(
        workspace_id=workspace_id,
        body=body,
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
        retry_num=x_slack_retry_num,
    )
    if not result.ok:
        raise HTTPException(status_code=401, detail={"error": result.error})
    drain = None
    if services.auto_drain_pipeline:
        if not isinstance(services.event_bus, InMemoryEventBus):
            raise HTTPException(
                status_code=500, detail="pipeline drain requires memory bus"
            )
        drain = await services.pipeline.drain(services.event_bus)
    payload: dict[str, object] = {"ok": True, "status": result.status}
    if result.challenge is not None:
        payload["challenge"] = result.challenge
    payload["raw_event_created"] = result.raw_event_created
    if drain is not None:
        payload["pipeline"] = {
            "processed_event_count": drain.processed_event_count,
            "normalization_count": drain.normalization_count,
            "chunking_count": drain.chunking_count,
            "embedding_count": drain.embedding_count,
        }
    return payload


@router.post("/backfill/{source_connection_id}")
async def backfill_source(
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
        requested_quantity=1,
    )
    services = get_slack_services(request)
    result = await services.backfill.backfill_source(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
    )
    drain = None
    if services.auto_drain_pipeline:
        if not isinstance(services.event_bus, InMemoryEventBus):
            raise HTTPException(
                status_code=500, detail="pipeline drain requires memory bus"
            )
        drain = await services.pipeline.drain(services.event_bus)
    response: dict[str, object] = {
        "ok": result.ok,
        "job": result.job.model_dump(mode="json"),
        "raw_events_created": result.raw_events_created,
        "duplicates": result.duplicates,
        "cursor_value": result.cursor_value,
    }
    if drain is not None:
        response["pipeline"] = {
            "processed_event_count": drain.processed_event_count,
            "normalization_count": drain.normalization_count,
            "chunking_count": drain.chunking_count,
            "embedding_count": drain.embedding_count,
        }
    return response


@router.get("/health/{workspace_id}")
async def slack_health(
    request: Request,
    workspace_id: str,
    context: TenantContext = TENANT_CONTEXT_DEPENDENCY,
) -> dict[str, object]:
    require_permission(
        context,
        workspace_id=workspace_id,
        permission=Permission.RETRIEVAL_READ,
    )
    return await get_slack_services(request).health.workspace_health(workspace_id)
