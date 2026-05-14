from __future__ import annotations

from collections.abc import Awaitable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from cortex.ingestion.payloads import sha256_digest
from cortex.permissions.provider_acls import (
    ProviderAclEntry,
    ProviderAclPrincipal,
    ProviderAclResourceRef,
    ProviderAclSnapshot,
)
from cortex.permissions.scopes import scope_external_id_hash
from cortex.utils.asyncio import maybe_await


class ProviderAclSnapshotRepository(Protocol):
    def replace_snapshot(
        self,
        *,
        workspace_id: str,
        resource: ProviderAclResourceRef,
        entries: list[ProviderAclEntry],
        captured_at: datetime | None = None,
        expires_at: datetime | None = None,
        source_connection_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> ProviderAclSnapshot | Awaitable[ProviderAclSnapshot]: ...

    def current_snapshot(
        self,
        *,
        workspace_id: str,
        resource: ProviderAclResourceRef,
    ) -> ProviderAclSnapshot | None | Awaitable[ProviderAclSnapshot | None]: ...


class SlackAclClient(Protocol):
    async def conversation_members(
        self,
        *,
        access_token: str,
        channel_id: str,
    ) -> list[str]: ...


class GitHubAclClient(Protocol):
    async def repository_collaborators(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
    ) -> list[str]: ...


class LinearAclClient(Protocol):
    async def team_members(
        self,
        *,
        api_token: str,
        team_id: str,
    ) -> list[str]: ...


@dataclass(frozen=True)
class ProviderAclIngestionResult:
    snapshot: ProviderAclSnapshot
    principal_count: int


@dataclass(frozen=True)
class ProviderAclFreshnessResource:
    workspace_id: str
    resource: ProviderAclResourceRef


@dataclass(frozen=True)
class ProviderAclFreshnessReport:
    current_count: int = 0
    expiring_soon_count: int = 0
    stale_count: int = 0
    missing_count: int = 0
    alerts: tuple[dict[str, object], ...] = field(default_factory=tuple)


class ProviderAclIngestionService:
    def __init__(
        self,
        repository: ProviderAclSnapshotRepository,
        *,
        ttl: timedelta = timedelta(hours=24),
    ) -> None:
        self.repository = repository
        self.ttl = ttl

    async def ingest_slack_channel_members(
        self,
        *,
        workspace_id: str,
        channel_id: str,
        member_user_ids: Sequence[str],
        source_connection_id: str | None = None,
        captured_at: datetime | None = None,
    ) -> ProviderAclIngestionResult:
        resource = slack_channel_resource(channel_id)
        return await self._replace_snapshot(
            workspace_id=workspace_id,
            resource=resource,
            provider="slack",
            principal_type="user",
            principal_external_ids=member_user_ids,
            source_connection_id=source_connection_id,
            captured_at=captured_at,
        )

    async def ingest_github_repository_collaborators(
        self,
        *,
        workspace_id: str,
        repository_id: str,
        collaborator_user_ids: Sequence[str],
        source_connection_id: str | None = None,
        captured_at: datetime | None = None,
    ) -> ProviderAclIngestionResult:
        resource = github_repository_resource(repository_id)
        return await self._replace_snapshot(
            workspace_id=workspace_id,
            resource=resource,
            provider="github",
            principal_type="user",
            principal_external_ids=collaborator_user_ids,
            source_connection_id=source_connection_id,
            captured_at=captured_at,
        )

    async def ingest_linear_team_members(
        self,
        *,
        workspace_id: str,
        team_id: str,
        member_user_ids: Sequence[str],
        source_connection_id: str | None = None,
        captured_at: datetime | None = None,
    ) -> ProviderAclIngestionResult:
        resource = linear_team_resource(team_id)
        return await self._replace_snapshot(
            workspace_id=workspace_id,
            resource=resource,
            provider="linear",
            principal_type="user",
            principal_external_ids=member_user_ids,
            source_connection_id=source_connection_id,
            captured_at=captured_at,
        )

    async def ingest_linear_project_members(
        self,
        *,
        workspace_id: str,
        project_id: str,
        member_user_ids: Sequence[str],
        source_connection_id: str | None = None,
        captured_at: datetime | None = None,
    ) -> ProviderAclIngestionResult:
        resource = linear_project_resource(project_id)
        return await self._replace_snapshot(
            workspace_id=workspace_id,
            resource=resource,
            provider="linear",
            principal_type="user",
            principal_external_ids=member_user_ids,
            source_connection_id=source_connection_id,
            captured_at=captured_at,
        )

    async def _replace_snapshot(
        self,
        *,
        workspace_id: str,
        resource: ProviderAclResourceRef,
        provider: str,
        principal_type: str,
        principal_external_ids: Sequence[str],
        source_connection_id: str | None,
        captured_at: datetime | None,
    ) -> ProviderAclIngestionResult:
        captured = captured_at or datetime.now(UTC)
        entries = [
            ProviderAclEntry(
                principal=ProviderAclPrincipal.from_external_id(
                    provider=provider,
                    principal_type=principal_type,
                    external_id=external_id,
                )
            )
            for external_id in sorted(set(principal_external_ids))
            if external_id
        ]
        snapshot = await maybe_await(
            self.repository.replace_snapshot(
                workspace_id=workspace_id,
                resource=resource,
                entries=entries,
                captured_at=captured,
                expires_at=captured + self.ttl,
                source_connection_id=source_connection_id,
                metadata_json={"principal_count": len(entries)},
            )
        )
        return ProviderAclIngestionResult(
            snapshot=snapshot,
            principal_count=len(entries),
        )


class ProviderAclProviderCollector:
    def __init__(
        self,
        ingestion: ProviderAclIngestionService,
        *,
        slack: SlackAclClient | None = None,
        github: GitHubAclClient | None = None,
        linear: LinearAclClient | None = None,
    ) -> None:
        self.ingestion = ingestion
        self.slack = slack
        self.github = github
        self.linear = linear

    async def collect_slack_channel(
        self,
        *,
        workspace_id: str,
        access_token: str,
        channel_id: str,
        source_connection_id: str | None = None,
    ) -> ProviderAclIngestionResult:
        if self.slack is None:
            raise RuntimeError("slack ACL client is not configured")
        members = await self.slack.conversation_members(
            access_token=access_token,
            channel_id=channel_id,
        )
        return await self.ingestion.ingest_slack_channel_members(
            workspace_id=workspace_id,
            channel_id=channel_id,
            member_user_ids=members,
            source_connection_id=source_connection_id,
        )

    async def collect_github_repository(
        self,
        *,
        workspace_id: str,
        access_token: str,
        owner: str,
        repo: str,
        repository_id: str,
        source_connection_id: str | None = None,
    ) -> ProviderAclIngestionResult:
        if self.github is None:
            raise RuntimeError("github ACL client is not configured")
        collaborators = await self.github.repository_collaborators(
            access_token=access_token,
            owner=owner,
            repo=repo,
        )
        return await self.ingestion.ingest_github_repository_collaborators(
            workspace_id=workspace_id,
            repository_id=repository_id,
            collaborator_user_ids=collaborators,
            source_connection_id=source_connection_id,
        )

    async def collect_linear_team(
        self,
        *,
        workspace_id: str,
        api_token: str,
        team_id: str,
        source_connection_id: str | None = None,
    ) -> ProviderAclIngestionResult:
        if self.linear is None:
            raise RuntimeError("linear ACL client is not configured")
        members = await self.linear.team_members(api_token=api_token, team_id=team_id)
        return await self.ingestion.ingest_linear_team_members(
            workspace_id=workspace_id,
            team_id=team_id,
            member_user_ids=members,
            source_connection_id=source_connection_id,
        )


class ProviderAclFreshnessService:
    def __init__(
        self,
        repository: ProviderAclSnapshotRepository,
        *,
        expiring_soon_window: timedelta = timedelta(hours=2),
    ) -> None:
        self.repository = repository
        self.expiring_soon_window = expiring_soon_window

    async def check_resources(
        self,
        resources: Sequence[ProviderAclFreshnessResource],
        *,
        now: datetime | None = None,
    ) -> ProviderAclFreshnessReport:
        current = now or datetime.now(UTC)
        counts = {
            "current": 0,
            "expiring_soon": 0,
            "stale": 0,
            "missing": 0,
        }
        alert_counts: dict[tuple[str, str, str], int] = {}
        for item in resources:
            snapshot = await maybe_await(
                self.repository.current_snapshot(
                    workspace_id=item.workspace_id,
                    resource=item.resource,
                )
            )
            status = _freshness_status(
                snapshot=snapshot,
                now=current,
                expiring_soon_window=self.expiring_soon_window,
            )
            counts[status] += 1
            if status in {"stale", "missing"}:
                key = (item.resource.provider, item.resource.resource_type, status)
                alert_counts[key] = alert_counts.get(key, 0) + 1
        alerts = tuple(
            {
                "provider": provider,
                "resource_type": resource_type,
                "status": status,
                "count": count,
            }
            for (provider, resource_type, status), count in sorted(alert_counts.items())
        )
        return ProviderAclFreshnessReport(
            current_count=counts["current"],
            expiring_soon_count=counts["expiring_soon"],
            stale_count=counts["stale"],
            missing_count=counts["missing"],
            alerts=alerts,
        )


def slack_channel_resource(channel_id: str) -> ProviderAclResourceRef:
    return ProviderAclResourceRef(
        provider="slack",
        resource_type="slack_channel",
        external_id_hash=sha256_digest(channel_id.encode()),
    )


def github_repository_resource(repository_id: str) -> ProviderAclResourceRef:
    return ProviderAclResourceRef(
        provider="github",
        resource_type="github_repository",
        external_id_hash=scope_external_id_hash(
            "github",
            "github_repository",
            repository_id,
        ),
    )


def linear_team_resource(team_id: str) -> ProviderAclResourceRef:
    return ProviderAclResourceRef(
        provider="linear",
        resource_type="linear_team",
        external_id_hash=scope_external_id_hash("linear", "linear_team", team_id),
    )


def linear_project_resource(project_id: str) -> ProviderAclResourceRef:
    return ProviderAclResourceRef(
        provider="linear",
        resource_type="linear_project",
        external_id_hash=scope_external_id_hash(
            "linear",
            "linear_project",
            project_id,
        ),
    )


def _freshness_status(
    *,
    snapshot: ProviderAclSnapshot | None,
    now: datetime,
    expiring_soon_window: timedelta,
) -> str:
    if snapshot is None:
        return "missing"
    if snapshot.expires_at <= now:
        return "stale"
    if snapshot.expires_at <= now + expiring_soon_window:
        return "expiring_soon"
    return "current"
