from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from cortex.connectors.slack.service import SlackConnectorServices

router = APIRouter(prefix="/connectors/slack", tags=["slack"])


def get_slack_services(request: Request) -> SlackConnectorServices:
    services = getattr(request.app.state, "slack_connector", None)
    if not isinstance(services, SlackConnectorServices):
        raise HTTPException(status_code=404, detail="slack connector is disabled")
    return services


@router.post("/oauth/start")
async def start_oauth(request: Request, body: dict[str, Any]) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")
    return get_slack_services(request).oauth.start_install(
        workspace_id=workspace_id,
        actor_id=str(body["actor_id"]) if "actor_id" in body else None,
    )


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


@router.post("/sources/select")
async def select_sources(request: Request, body: dict[str, Any]) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    installation_id = str(body.get("oauth_installation_id", ""))
    channels = body.get("channels", [])
    if not workspace_id or not installation_id or not isinstance(channels, list):
        raise HTTPException(status_code=422, detail="invalid source selection")
    return get_slack_services(request).sources.select_channels(
        workspace_id=workspace_id,
        oauth_installation_id=installation_id,
        channels=[dict(channel) for channel in channels],
    )


@router.post("/events")
async def slack_events(
    request: Request,
    x_slack_request_timestamp: str = Header(default=""),
    x_slack_signature: str = Header(default=""),
    x_slack_retry_num: str | None = Header(default=None),
) -> dict[str, object]:
    workspace_id = request.query_params.get("workspace_id", "ws_1")
    body = await request.body()
    result = await get_slack_services(request).webhooks.handle(
        workspace_id=workspace_id,
        body=body,
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
        retry_num=x_slack_retry_num,
    )
    if not result.ok:
        raise HTTPException(status_code=401, detail={"error": result.error})
    payload: dict[str, object] = {"ok": True, "status": result.status}
    if result.challenge is not None:
        payload["challenge"] = result.challenge
    payload["raw_event_created"] = result.raw_event_created
    return payload


@router.post("/backfill/{source_connection_id}")
async def backfill_source(
    request: Request, source_connection_id: str, body: dict[str, Any]
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")
    result = await get_slack_services(request).backfill.backfill_source(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
    )
    return {
        "ok": result.ok,
        "job": result.job.model_dump(mode="json"),
        "raw_events_created": result.raw_events_created,
        "duplicates": result.duplicates,
        "cursor_value": result.cursor_value,
    }


@router.get("/health/{workspace_id}")
async def slack_health(request: Request, workspace_id: str) -> dict[str, object]:
    return get_slack_services(request).health.workspace_health(workspace_id)
