from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from cortex.connectors.github.service import GitHubConnectorServices

router = APIRouter(prefix="/connectors/github", tags=["github"])


def get_github_services(request: Request) -> GitHubConnectorServices:
    services = getattr(request.app.state, "github_connector", None)
    if not isinstance(services, GitHubConnectorServices):
        raise HTTPException(status_code=404, detail="github connector is disabled")
    return services


@router.post("/install/app")
async def install_app(request: Request, body: dict[str, Any]) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    if not workspace_id:
        raise HTTPException(status_code=422, detail="workspace_id is required")
    return get_github_services(request).install_app(
        workspace_id=workspace_id,
        app_id=str(body.get("app_id", "")),
        private_key=str(body.get("private_key", "")),
    )


@router.post("/sources/select")
async def select_repos(request: Request, body: dict[str, Any]) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    repos = body.get("repos", [])
    if not workspace_id or not isinstance(repos, list):
        raise HTTPException(status_code=422, detail="invalid repo selection")
    return get_github_services(request).select_repos(
        workspace_id=workspace_id,
        repos=[dict(repo) for repo in repos],
    )


@router.post("/backfill/{source_connection_id}")
async def backfill(
    request: Request, source_connection_id: str, body: dict[str, Any]
) -> dict[str, object]:
    workspace_id = str(body.get("workspace_id", ""))
    events = body.get("events", [])
    if not workspace_id or not isinstance(events, list):
        raise HTTPException(status_code=422, detail="workspace_id and events required")
    return await get_github_services(request).backfill(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        events=[dict(event) for event in events],
    )


@router.post("/events")
async def github_events(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default="event"),
    x_github_delivery: str = Header(default=""),
) -> dict[str, object]:
    workspace_id = request.query_params.get("workspace_id", "ws_1")
    source_connection_id = request.query_params.get(
        "source_connection_id", "src_github"
    )
    return await get_github_services(request).webhook(
        workspace_id=workspace_id,
        source_connection_id=source_connection_id,
        body=await request.body(),
        signature=x_hub_signature_256,
        event_name=x_github_event,
        delivery_id=x_github_delivery or "delivery",
    )


@router.get("/health/{workspace_id}")
async def health(request: Request, workspace_id: str) -> dict[str, object]:
    return get_github_services(request).health(workspace_id)
