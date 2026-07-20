"""Credential-free readers for redacted demo-run reporting."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.dev.workbench import DevWorkbenchService

from .contracts import DemoRunReport, LiveRunCounts, SourceHealth
from .repositories import SqlAlchemyDemoRunReportRepository


class DemoRunReportReader(Protocol):
    """Adapter boundary for a durable report projection owned elsewhere."""

    async def latest_report(
        self, *, workspace_id: str, trace_id: str
    ) -> DemoRunReport | None: ...


class SourceHealthReader(Protocol):
    """Optional adapter boundary for redacted per-source health."""

    async def source_health(
        self, *, workspace_id: str, trace_id: str
    ) -> tuple[SourceHealth, ...] | None: ...


class SqlAlchemyDemoRunReportStore:
    """Session-factory adapter for trusted finalizers and read-only API views.

    The store does not synthesize a report from mutable workspace-wide tables.
    Its write method is an internal seam for a future exact membership-aware
    finalizer; no browser or MCP write route is exposed.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def latest_report(
        self, *, workspace_id: str, trace_id: str
    ) -> DemoRunReport | None:
        # Trace IDs are deliberately not persisted into this redacted report
        # projection. They remain request-scoped observability data.
        del trace_id
        async with self.session_factory() as session:
            return await SqlAlchemyDemoRunReportRepository(session).latest_report(
                workspace_id=workspace_id
            )

    async def record_report(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        report: DemoRunReport,
    ) -> DemoRunReport:
        """Commit an already-finalized immutable report from trusted runtime code."""
        async with self.session_factory() as session:
            persisted = await SqlAlchemyDemoRunReportRepository(session).record_report(
                workspace_id=workspace_id,
                source_connection_id=source_connection_id,
                report=report,
            )
            await session.commit()
            return persisted


class FixtureDemoRunReportReader:
    """Provide fixture source health without fabricating a persisted live run.

    A valid ``live-context-run-report/v1`` proves a controlled Slack run and
    requires ``live_data: true``.  Fixtures cannot make that claim, so
    ``latest_report`` returns ``None``.  The source-health view is still useful
    for local UI development and is explicitly labelled ``fixture``.
    """

    async def latest_report(
        self, *, workspace_id: str, trace_id: str
    ) -> DemoRunReport | None:
        return None

    async def source_health(
        self, *, workspace_id: str, trace_id: str
    ) -> tuple[SourceHealth, ...]:
        workbench = await self._workbench()
        provider_counts = Counter(
            item.provider for item in workbench.repository.source_objects.values()
        )
        return tuple(
            SourceHealth(
                source_ref_hash=_hash(f"fixture:{provider}"),
                provider=provider,
                mode="fixture",
                readiness="partial",
                freshness="fresh",
                freshness_seconds=0,
                counts=LiveRunCounts(
                    raw_events=count,
                    source_objects=count,
                    source_chunks=count,
                    embeddings_completed=count,
                    vector_points_verified=0,
                    query_requests=0,
                    evidence_packs=0,
                    failures=0,
                ),
            )
            for provider, count in sorted(provider_counts.items())
        )

    async def _workbench(self) -> DevWorkbenchService:
        workbench = DevWorkbenchService()
        workbench.seed()
        await workbench.run_pipeline()
        workbench.query("fixture-demo-run")
        return workbench


def _hash(value: str) -> str:
    return f"sha256:{sha256(value.encode()).hexdigest()}"
