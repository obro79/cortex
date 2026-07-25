"""Authenticated, redacted demo-run control-plane reads.

The application registers this router in every profile. A durable reader is
installed only for SQL state; fixture mode substitutes a fixture-health reader
that never fabricates a ``live_data: true`` report. Any missing or invalid
projection is reported explicitly as unavailable.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from cortex.auth.dependencies import require_tenant_context
from cortex.demo_runs import (
    DemoRunReportReader,
    DemoRunReportStatus,
    ReportIssue,
    SourceHealthReader,
    SourceHealthStatus,
)
from cortex.demo_runs.contracts import Freshness, Readiness, SourceHealth
from cortex.observability.tracing import ensure_trace_context
from cortex.tenancy import TenantContext

router = APIRouter(prefix="/v1/demo-runs", tags=["demo-runs"])
TenantDependency = Annotated[TenantContext, Depends(require_tenant_context)]

_UNAVAILABLE = ReportIssue(code="demo_run_report_unavailable", severity="warning")


def _reader(request: Request) -> DemoRunReportReader | None:
    candidate = getattr(request.app.state, "demo_run_report_reader", None)
    if candidate is None or not hasattr(candidate, "latest_report"):
        return None
    return cast(DemoRunReportReader, candidate)


def _source_health_reader(request: Request) -> SourceHealthReader | None:
    candidate = getattr(request.app.state, "demo_run_report_reader", None)
    if candidate is None or not hasattr(candidate, "source_health"):
        return None
    return cast(SourceHealthReader, candidate)


def _hash(value: str) -> str:
    return f"sha256:{sha256(value.encode()).hexdigest()}"


async def _status(
    request: Request, context: TenantContext
) -> tuple[str, DemoRunReportStatus]:
    trace = ensure_trace_context(
        trace_id=context.trace_id, workspace_id=context.workspace_id
    )
    reader = _reader(request)
    trace_id_hash = _hash(trace.trace_id)
    if reader is None:
        return trace_id_hash, DemoRunReportStatus(
            trace_id_hash=trace_id_hash,
            available=False,
            report=None,
            issues=(_UNAVAILABLE,),
        )
    try:
        report = await reader.latest_report(
            workspace_id=context.workspace_id,
            trace_id=trace.trace_id,
        )
    except Exception:
        # This is a safe status surface. A projection/database failure must not
        # leak implementation detail or turn a missing report into an API 500.
        report = None
    if report is None:
        return trace_id_hash, DemoRunReportStatus(
            trace_id_hash=trace_id_hash,
            available=False,
            report=None,
            issues=(_UNAVAILABLE,),
        )
    return trace_id_hash, DemoRunReportStatus(
        trace_id_hash=trace_id_hash,
        available=True,
        report=report,
    )


@router.get("/latest", response_model=DemoRunReportStatus)
async def latest_demo_run(
    request: Request, context: TenantDependency
) -> DemoRunReportStatus:
    """Read the newest aggregate demo report for the authenticated workspace."""
    _, result = await _status(request, context)
    return result


@router.get("/source-health", response_model=SourceHealthStatus)
async def source_health(
    request: Request, context: TenantDependency
) -> SourceHealthStatus:
    """Read only safe source status/counts from the configured projection."""
    trace = ensure_trace_context(
        trace_id=context.trace_id, workspace_id=context.workspace_id
    )
    trace_id_hash = _hash(trace.trace_id)
    reader = _source_health_reader(request)
    if reader is None:
        return SourceHealthStatus(
            trace_id_hash=trace_id_hash,
            available=False,
            readiness="unavailable",
            freshness="unknown",
            issues=(_UNAVAILABLE,),
        )
    try:
        sources = await reader.source_health(
            workspace_id=context.workspace_id,
            trace_id=trace.trace_id,
        )
    except Exception:
        sources = None
    if sources is None:
        return SourceHealthStatus(
            trace_id_hash=trace_id_hash,
            available=False,
            readiness="unavailable",
            freshness="unknown",
            issues=(_UNAVAILABLE,),
        )
    return SourceHealthStatus(
        trace_id_hash=trace_id_hash,
        available=True,
        readiness=_source_readiness(sources),
        freshness=_freshness(sources),
        sources=sources,
        issues=(),
    )


def _freshness(sources: tuple[SourceHealth, ...]) -> Freshness:
    values = {getattr(source, "freshness", "unknown") for source in sources}
    if "stale" in values:
        return "stale"
    if values == {"fresh"}:
        return "fresh"
    return "unknown"


def _source_readiness(sources: tuple[SourceHealth, ...]) -> Readiness:
    values = {source.readiness for source in sources}
    if "not_ready" in values:
        return "not_ready"
    if "partial" in values:
        return "partial"
    if values == {"ready"}:
        return "ready"
    return "unavailable"
