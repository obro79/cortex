from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cortex.ingestion.payloads import sha256_digest
from cortex.permissions import (
    InMemoryProviderAclRepository,
    InMemoryProviderPrincipalMappingRepository,
    ProviderAclFreshnessResource,
    ProviderAclFreshnessService,
    ProviderAclIngestionService,
    ProviderAclPrincipal,
    ProviderAclProviderCollector,
)
from cortex.permissions.provider_acl_ingestion import (
    github_repository_resource,
    linear_team_resource,
    slack_channel_resource,
)


class FakeSlackAclClient:
    async def conversation_members(
        self,
        *,
        access_token: str,
        channel_id: str,
    ) -> list[str]:
        assert access_token == "xoxb_test"
        assert channel_id == "C123"
        return ["U1", "U2"]


class FakeGitHubAclClient:
    async def repository_collaborators(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
    ) -> list[str]:
        assert access_token == "ghs_test"
        assert (owner, repo) == ("acme", "app")
        return ["1001", "1002"]


class FakeLinearAclClient:
    async def team_members(self, *, api_token: str, team_id: str) -> list[str]:
        assert api_token == "lin_test"
        assert team_id == "team_1"
        return ["lin_user_1"]


@pytest.mark.asyncio
async def test_provider_acl_ingestion_hashes_resources_and_principals() -> None:
    repository = InMemoryProviderAclRepository()
    service = ProviderAclIngestionService(repository)

    result = await service.ingest_slack_channel_members(
        workspace_id="ws_1",
        channel_id="C123",
        member_user_ids=["U1", "U2", "U1"],
        captured_at=datetime(2026, 5, 14, tzinfo=UTC),
    )
    principal = ProviderAclPrincipal.from_external_id(
        provider="slack",
        principal_type="user",
        external_id="U1",
    )
    decision = repository.authorize(
        workspace_id="ws_1",
        resource=slack_channel_resource("C123"),
        principals=[principal],
        now=datetime(2026, 5, 14, tzinfo=UTC),
    )

    assert result.principal_count == 2
    assert result.snapshot.resource.external_id_hash == sha256_digest(b"C123")
    assert decision.allowed is True
    raw_snapshot_text = repr(result.snapshot)
    assert "U1" not in raw_snapshot_text
    assert "U2" not in raw_snapshot_text
    assert "C123" not in raw_snapshot_text


@pytest.mark.asyncio
async def test_provider_acl_collector_pulls_from_provider_clients() -> None:
    repository = InMemoryProviderAclRepository()
    ingestion = ProviderAclIngestionService(repository)
    collector = ProviderAclProviderCollector(
        ingestion,
        slack=FakeSlackAclClient(),
        github=FakeGitHubAclClient(),
        linear=FakeLinearAclClient(),
    )

    slack = await collector.collect_slack_channel(
        workspace_id="ws_1",
        access_token="xoxb_test",
        channel_id="C123",
    )
    github = await collector.collect_github_repository(
        workspace_id="ws_1",
        access_token="ghs_test",
        owner="acme",
        repo="app",
        repository_id="42",
    )
    linear = await collector.collect_linear_team(
        workspace_id="ws_1",
        api_token="lin_test",
        team_id="team_1",
    )

    assert slack.snapshot.resource == slack_channel_resource("C123")
    assert github.snapshot.resource == github_repository_resource("42")
    assert linear.snapshot.resource == linear_team_resource("team_1")


def test_provider_principal_mapping_resolves_active_non_expired_principals() -> None:
    repository = InMemoryProviderPrincipalMappingRepository()
    now = datetime(2026, 5, 14, tzinfo=UTC)
    active = repository.upsert_mapping(
        workspace_id="ws_1",
        user_id="usr_1",
        provider="github",
        principal_type="user",
        external_id="1001",
        match_method="verified_email",
        last_verified_at=now,
        expires_at=now + timedelta(days=1),
    )
    repository.upsert_mapping(
        workspace_id="ws_1",
        user_id="usr_1",
        provider="slack",
        principal_type="user",
        external_id="U1",
        match_method="verified_email",
        last_verified_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
    )

    principals = repository.active_principals(
        workspace_id="ws_1",
        user_id="usr_1",
        now=now,
    )

    assert principals == [active.principal]
    assert "1001" not in repr(active)


@pytest.mark.asyncio
async def test_provider_acl_freshness_reports_safe_stale_and_missing_alerts() -> None:
    repository = InMemoryProviderAclRepository()
    service = ProviderAclIngestionService(repository, ttl=timedelta(minutes=30))
    now = datetime(2026, 5, 14, tzinfo=UTC)
    await service.ingest_github_repository_collaborators(
        workspace_id="ws_1",
        repository_id="repo_current",
        collaborator_user_ids=["1001"],
        captured_at=now,
    )
    await service.ingest_github_repository_collaborators(
        workspace_id="ws_1",
        repository_id="repo_stale",
        collaborator_user_ids=["1002"],
        captured_at=now - timedelta(hours=2),
    )
    freshness = ProviderAclFreshnessService(repository)

    report = await freshness.check_resources(
        [
            ProviderAclFreshnessResource(
                workspace_id="ws_1",
                resource=github_repository_resource("repo_current"),
            ),
            ProviderAclFreshnessResource(
                workspace_id="ws_1",
                resource=github_repository_resource("repo_stale"),
            ),
            ProviderAclFreshnessResource(
                workspace_id="ws_1",
                resource=github_repository_resource("repo_missing"),
            ),
        ],
        now=now,
    )

    assert report.expiring_soon_count == 1
    assert report.stale_count == 1
    assert report.missing_count == 1
    assert report.alerts == (
        {
            "provider": "github",
            "resource_type": "github_repository",
            "status": "missing",
            "count": 1,
        },
        {
            "provider": "github",
            "resource_type": "github_repository",
            "status": "stale",
            "count": 1,
        },
    )
    assert "repo_stale" not in repr(report.alerts)
    assert "1002" not in repr(report.alerts)
