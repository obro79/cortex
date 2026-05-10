from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cortex.contracts.entities import (
    BackfillJob,
    OAuthInstallation,
    SourceConnection,
)
from cortex.ingestion.payloads import sha256_digest
from cortex.utils.asyncio import maybe_await


@dataclass(frozen=True)
class SourceHealthRow:
    provider: str
    source_type: str
    source_connection_id: str
    source_fingerprint: str
    selected: bool
    source_status: str
    oauth_status: str
    provider_workspace_id: str
    cursor_high_watermark: str | None
    cursor_updated_at: datetime | None
    latest_backfill_status: str | None
    latest_backfill_updated_at: datetime | None


@dataclass(frozen=True)
class ConnectorSummary:
    provider: str
    workspace_id: str
    oauth_status: str
    provider_workspace_id: str
    selected_source_count: int
    cursor_count: int
    latest_backfill_status: str | None


@dataclass(frozen=True)
class SourceHealthView:
    workspace_id: str
    connectors: list[ConnectorSummary]
    sources: list[SourceHealthRow]


class SourceHealthViewService:
    def __init__(self, *, slack_connector: Any | None = None) -> None:
        self.slack_connector = slack_connector

    async def build(self, workspace_id: str) -> SourceHealthView:
        if self.slack_connector is None:
            return SourceHealthView(
                workspace_id=workspace_id,
                connectors=[],
                sources=[],
            )
        installations = await maybe_await(
            self.slack_connector.installations.list_for_workspace(workspace_id)
        )
        sources = await maybe_await(
            self.slack_connector.source_connections.list_selected(workspace_id)
        )
        jobs = await maybe_await(
            self.slack_connector.backfills.list_for_workspace(workspace_id)
        )
        rows = [
            await self._source_row(
                workspace_id=workspace_id,
                source=source,
                installations=installations,
                jobs=jobs,
            )
            for source in sources
        ]
        connectors = self._connector_summaries(
            workspace_id=workspace_id,
            installations=installations,
            sources=sources,
            rows=rows,
            jobs=jobs,
        )
        return SourceHealthView(
            workspace_id=workspace_id,
            connectors=connectors,
            sources=rows,
        )

    async def _source_row(
        self,
        *,
        workspace_id: str,
        source: SourceConnection,
        installations: list[OAuthInstallation],
        jobs: list[BackfillJob],
    ) -> SourceHealthRow:
        slack_connector = self.slack_connector
        if slack_connector is None:
            raise RuntimeError("Slack connector is not configured")
        cursor = await maybe_await(
            slack_connector.cursors.get_for_source(
                workspace_id=workspace_id,
                source_connection_id=source.id,
            )
        )
        installation = _find_installation(installations, source.oauth_installation_id)
        latest_job = _latest_job_for_source(jobs, source.id)
        return SourceHealthRow(
            provider=source.provider,
            source_type=source.source_type,
            source_connection_id=source.id,
            source_fingerprint=_fingerprint(source.external_source_id),
            selected=source.selected,
            source_status=_status_value(source.status),
            oauth_status=_status_value(installation.status)
            if installation
            else "missing",
            provider_workspace_id=(
                installation.provider_workspace_id if installation else "unknown"
            ),
            cursor_high_watermark=cursor.high_watermark if cursor else None,
            cursor_updated_at=cursor.updated_at if cursor else None,
            latest_backfill_status=_status_value(latest_job.status)
            if latest_job
            else None,
            latest_backfill_updated_at=latest_job.updated_at if latest_job else None,
        )

    def _connector_summaries(
        self,
        *,
        workspace_id: str,
        installations: list[OAuthInstallation],
        sources: list[SourceConnection],
        rows: list[SourceHealthRow],
        jobs: list[BackfillJob],
    ) -> list[ConnectorSummary]:
        summaries: list[ConnectorSummary] = []
        for installation in installations:
            install_sources = [
                source
                for source in sources
                if source.oauth_installation_id == installation.id
            ]
            cursor_count = len(
                [
                    row
                    for row in rows
                    if row.provider_workspace_id == installation.provider_workspace_id
                    and row.cursor_high_watermark is not None
                ]
            )
            summaries.append(
                ConnectorSummary(
                    provider=installation.provider,
                    workspace_id=workspace_id,
                    oauth_status=_status_value(installation.status),
                    provider_workspace_id=installation.provider_workspace_id,
                    selected_source_count=len(install_sources),
                    cursor_count=cursor_count,
                    latest_backfill_status=_latest_job_status(jobs, install_sources),
                )
            )
        if not summaries and self.slack_connector is not None:
            summaries.append(
                ConnectorSummary(
                    provider="slack",
                    workspace_id=workspace_id,
                    oauth_status="not_installed",
                    provider_workspace_id="unknown",
                    selected_source_count=0,
                    cursor_count=0,
                    latest_backfill_status=None,
                )
            )
        return summaries


def _find_installation(
    installations: list[OAuthInstallation], installation_id: str
) -> OAuthInstallation | None:
    return next(
        (
            installation
            for installation in installations
            if installation.id == installation_id
        ),
        None,
    )


def _latest_job_for_source(
    jobs: list[BackfillJob], source_connection_id: str
) -> BackfillJob | None:
    source_jobs = [
        job for job in jobs if job.source_connection_id == source_connection_id
    ]
    return max(source_jobs, key=lambda job: job.updated_at, default=None)


def _latest_job_status(
    jobs: list[BackfillJob], sources: list[SourceConnection]
) -> str | None:
    source_ids = {source.id for source in sources}
    latest = max(
        (job for job in jobs if job.source_connection_id in source_ids),
        key=lambda job: job.updated_at,
        default=None,
    )
    return _status_value(latest.status) if latest else None


def _fingerprint(value: str) -> str:
    return sha256_digest(value.encode()).removeprefix("sha256:")[:12]


def _status_value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    return str(enum_value if enum_value is not None else value)
