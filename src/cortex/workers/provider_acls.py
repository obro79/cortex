from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cortex.config import Settings
from cortex.connectors.github.client import RealGitHubClient
from cortex.connectors.linear.client import RealLinearClient
from cortex.connectors.slack.client import RealSlackWebClient
from cortex.permissions import (
    ProviderAclFreshnessService,
    ProviderAclIngestionService,
    ProviderAclProviderCollector,
    ProviderAclRefreshResult,
    ProviderAclRefreshService,
    ProviderAclRefreshTarget,
    ProviderPrincipalMappingInput,
    SqlAlchemyProviderAclRepository,
    SqlAlchemyProviderPrincipalMappingRepository,
)
from cortex.platform import (
    ScheduledJob,
    ScheduledJobResult,
    SingletonJobRunner,
    SqlAlchemySchedulerLeaseRepository,
)


@dataclass(frozen=True)
class ProviderAclWorkerRunResult:
    scheduler: ScheduledJobResult
    refresh: ProviderAclRefreshResult | None = None

    @property
    def resources_attempted(self) -> int:
        return self.refresh.resources_attempted if self.refresh is not None else 0

    @property
    def resources_refreshed(self) -> int:
        return self.refresh.resources_refreshed if self.refresh is not None else 0

    @property
    def failures(self) -> int:
        return len(self.refresh.failures) if self.refresh is not None else 0


async def process_provider_acl_refresh_once(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    worker_id: str,
) -> ProviderAclWorkerRunResult:
    targets = provider_acl_refresh_targets_from_json(
        settings.cortex_provider_acl_refresh_targets_json
    )
    mappings = provider_acl_principal_mappings_from_json(
        settings.cortex_provider_acl_principal_mappings_json
    )
    async with session_factory() as session:
        try:
            refresh_result: ProviderAclRefreshResult | None = None

            async def refresh_provider_acls() -> None:
                nonlocal refresh_result
                repository = SqlAlchemyProviderAclRepository(session)
                ingestion = ProviderAclIngestionService(
                    repository,
                    ttl=timedelta(
                        hours=settings.cortex_provider_acl_snapshot_ttl_hours
                    ),
                )
                collector = ProviderAclProviderCollector(
                    ingestion,
                    slack=RealSlackWebClient(),
                    github=RealGitHubClient(),
                    linear=RealLinearClient(),
                )
                refresh = ProviderAclRefreshService(
                    collector,
                    ProviderAclFreshnessService(repository),
                    principal_mappings=SqlAlchemyProviderPrincipalMappingRepository(
                        session
                    ),
                    token_resolver=_token_from_env,
                )
                refresh_result = await refresh.refresh(
                    targets=targets,
                    principal_mappings=mappings,
                )

            runner = SingletonJobRunner(
                SqlAlchemySchedulerLeaseRepository(session),
                owner_id=worker_id,
            )
            scheduler_result = await runner.run_once(
                ScheduledJob(
                    name="provider-acl-refresh",
                    lease_ttl_seconds=(
                        settings.cortex_provider_acl_refresh_lease_ttl_seconds
                    ),
                    handler=refresh_provider_acls,
                )
            )
            await session.commit()
            return ProviderAclWorkerRunResult(
                scheduler=scheduler_result,
                refresh=refresh_result,
            )
        except Exception:
            await session.rollback()
            raise


def provider_acl_refresh_targets_from_json(
    value: str,
) -> tuple[ProviderAclRefreshTarget, ...]:
    items = _json_items(value, key="targets")
    return tuple(_target_from_mapping(item) for item in items)


def provider_acl_principal_mappings_from_json(
    value: str,
) -> tuple[ProviderPrincipalMappingInput, ...]:
    items = _json_items(value, key="mappings")
    return tuple(_principal_mapping_from_mapping(item) for item in items)


def _target_from_mapping(item: dict[str, Any]) -> ProviderAclRefreshTarget:
    _reject_inline_secret(item)
    provider = _required_str(item, "provider")
    resource_type = _required_str(item, "resource_type")
    return ProviderAclRefreshTarget(
        workspace_id=_required_str(item, "workspace_id"),
        provider=provider,
        resource_type=resource_type,
        external_id=_target_external_id(item, provider=provider),
        token_env=_required_str(item, "token_env"),
        source_connection_id=_optional_str(item, "source_connection_id"),
        owner=_optional_str(item, "owner"),
        repo=_optional_str(item, "repo"),
    )


def _principal_mapping_from_mapping(
    item: dict[str, Any],
) -> ProviderPrincipalMappingInput:
    _reject_inline_secret(item)
    return ProviderPrincipalMappingInput(
        workspace_id=_required_str(item, "workspace_id"),
        user_id=_required_str(item, "user_id"),
        provider=_required_str(item, "provider"),
        principal_type=str(item.get("principal_type") or "user"),
        external_id=_required_str(item, "external_id"),
        match_method=str(item.get("match_method") or "admin_configured"),
    )


def _json_items(value: str, *, key: str) -> list[dict[str, Any]]:
    if not value.strip():
        return []
    decoded = json.loads(value)
    if isinstance(decoded, dict):
        decoded = decoded.get(key, [])
    if not isinstance(decoded, list):
        raise ValueError(f"provider ACL {key} JSON must be a list")
    items: list[dict[str, Any]] = []
    for item in decoded:
        if not isinstance(item, dict):
            raise ValueError(f"provider ACL {key} entries must be objects")
        items.append(item)
    return items


def _target_external_id(item: dict[str, Any], *, provider: str) -> str:
    for key in (
        "external_id",
        "channel_id",
        "repository_id",
        "team_id",
    ):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    raise ValueError(f"{provider} ACL target requires an external resource id")


def _required_str(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"provider ACL config requires {key}")
    return value


def _optional_str(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    return value if isinstance(value, str) and value else None


def _reject_inline_secret(item: dict[str, Any]) -> None:
    forbidden = {"token", "access_token", "api_token", "secret"}
    present = forbidden.intersection(item)
    if present:
        raise ValueError(
            "provider ACL config must use token_env, not inline secret fields"
        )


def _token_from_env(target: ProviderAclRefreshTarget) -> str | None:
    return os.environ.get(target.token_env)
