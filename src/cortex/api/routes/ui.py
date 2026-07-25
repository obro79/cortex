from __future__ import annotations

import secrets
from html import escape

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from cortex.config import Settings
from cortex.ui.auth import resolve_ui_actor_context, set_internal_session_cookies
from cortex.ui.render import render_shell
from cortex.ui.source_health import (
    ConnectorSummary,
    SourceHealthRow,
    SourceHealthViewService,
)

router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/internal/session/start")
async def start_internal_session(
    request: Request,
    workspace_id: str = "ws_live_slack",
    actor_id: str = "local_admin",
) -> RedirectResponse:
    settings = _settings(request)
    if settings.cortex_env not in {"local", "test"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if not settings.cortex_internal_admin_session_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="internal admin sessions are disabled",
        )
    response = RedirectResponse("/ui", status_code=status.HTTP_303_SEE_OTHER)
    set_internal_session_cookies(
        response,
        workspace_id=workspace_id,
        actor_id=actor_id,
        roles=frozenset({"workspace_admin"}),
        session_id=secrets.token_hex(16),
    )
    return response


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def ui_overview(request: Request) -> str:
    context = resolve_ui_actor_context(request)
    body = f"""
    <section class="panel">
      <h2>Operations Overview</h2>
      <p class="meta">
        Phase 14 UI shell is enabled for authenticated internal admins.
      </p>
      <div class="grid">
        <div>
          <span class="status">ready</span>
          <h2>Sources</h2>
          <p class="meta">Real source health read model lands next.</p>
        </div>
        <div>
          <span class="status">ready</span>
          <h2>Evidence</h2>
          <p class="meta">
            Evidence-pack inspector will read from retrieval stores.
          </p>
        </div>
        <div>
          <span class="status">ready</span>
          <h2>Jobs</h2>
          <p class="meta">
            Backfill and replay status will use support-operation data.
          </p>
        </div>
      </div>
    </section>
    <section class="panel" style="margin-top:12px">
      <h2>Session</h2>
      <p class="meta">Trace {escape(context.trace_id)}</p>
      <p class="meta">CSRF token issued for mutating UI actions.</p>
    </section>
    """
    return render_shell(context=context, title="Operations Overview", body=body)


@router.get("/sources", response_class=HTMLResponse)
async def ui_sources(request: Request) -> str:
    context = resolve_ui_actor_context(request)
    view = await _source_health_view(request).build(context.workspace_id)
    rows = "\n".join(
        _source_row_html(row)
        for row in sorted(view.sources, key=lambda item: item.source_connection_id)
    )
    if not rows:
        rows = """
        <tr>
          <td colspan="8" class="meta">No selected sources for this workspace.</td>
        </tr>
        """
    body = f"""
    <section class="panel">
      <h2>Source Health</h2>
      <p class="meta">
        Selected sources, cursors, and backfill state from live repositories.
      </p>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Source</th>
              <th>Status</th>
              <th>OAuth</th>
              <th>Team</th>
              <th>Cursor</th>
              <th>Cursor Updated</th>
              <th>Backfill</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>
    """
    return render_shell(context=context, title="Source Health", body=body)


@router.get("/connectors", response_class=HTMLResponse)
async def ui_connectors(request: Request) -> str:
    context = resolve_ui_actor_context(request)
    view = await _source_health_view(request).build(context.workspace_id)
    rows = "\n".join(
        _connector_row_html(connector)
        for connector in sorted(view.connectors, key=lambda item: item.provider)
    )
    if not rows:
        rows = """
        <tr>
          <td colspan="7" class="meta">No connector state for this workspace.</td>
        </tr>
        """
    body = f"""
    <section class="panel">
      <h2>Connectors</h2>
      <p class="meta">
        OAuth, selected source, cursor, and latest backfill summary.
      </p>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Workspace</th>
              <th>OAuth</th>
              <th>Provider Workspace</th>
              <th>Selected</th>
              <th>Cursors</th>
              <th>Latest Backfill</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>
    """
    return render_shell(context=context, title="Connectors", body=body)


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are not configured")
    return settings


def _source_health_view(request: Request) -> SourceHealthViewService:
    service = getattr(request.app.state, "source_health_view", None)
    if not isinstance(service, SourceHealthViewService):
        raise RuntimeError("source health view service is not configured")
    return service


def _source_row_html(source: SourceHealthRow) -> str:
    return f"""
    <tr>
      <td>{escape(source.provider)}</td>
      <td>{escape(source.source_type)}:{escape(source.source_fingerprint)}</td>
      <td><span class="status">{escape(source.source_status)}</span></td>
      <td>{escape(source.oauth_status)}</td>
      <td>{escape(source.provider_workspace_id)}</td>
      <td>{escape(source.cursor_high_watermark or "none")}</td>
      <td>{escape(_format_timestamp(source.cursor_updated_at))}</td>
      <td>{escape(source.latest_backfill_status or "none")}</td>
    </tr>
    """


def _connector_row_html(item: ConnectorSummary) -> str:
    return f"""
    <tr>
      <td>{escape(item.provider)}</td>
      <td>{escape(item.workspace_id)}</td>
      <td><span class="status">{escape(item.oauth_status)}</span></td>
      <td>{escape(item.provider_workspace_id)}</td>
      <td>{item.selected_source_count}</td>
      <td>{item.cursor_count}</td>
      <td>{escape(item.latest_backfill_status or "none")}</td>
    </tr>
    """


def _format_timestamp(value: object) -> str:
    if value is None:
        return "none"
    return str(value)
