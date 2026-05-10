from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from cortex.config import Settings

EmbeddingMode = Literal["deterministic", "real"]


@dataclass(frozen=True)
class FeatureFlags:
    dev_workbench_enabled: bool
    slack_connector_enabled: bool
    linear_connector_enabled: bool
    github_connector_enabled: bool
    repo_docs_connector_enabled: bool
    ui_enabled: bool
    internal_admin_session_enabled: bool
    context_gate_blocking_enabled: bool
    embedding_mode: EmbeddingMode
    api_rate_limit_enabled: bool
    provider_rate_limit_enabled: bool
    model_rate_limit_enabled: bool
    cache_backend: Literal["memory", "redis"]

    def sanitized_dict(self) -> dict[str, object]:
        return asdict(self)

    def production_violations(self) -> list[str]:
        violations: list[str] = []
        if self.dev_workbench_enabled:
            violations.append("dev_workbench_enabled")
        if self.internal_admin_session_enabled:
            violations.append("internal_admin_session_enabled")
        if self.cache_backend == "memory" and (
            self.api_rate_limit_enabled
            or self.provider_rate_limit_enabled
            or self.model_rate_limit_enabled
        ):
            violations.append("memory_cache_with_rate_limits")
        return violations


def feature_flags_from_settings(settings: Settings) -> FeatureFlags:
    return FeatureFlags(
        dev_workbench_enabled=settings.cortex_dev_workbench_enabled,
        slack_connector_enabled=settings.cortex_slack_connector_enabled,
        linear_connector_enabled=settings.cortex_linear_connector_enabled,
        github_connector_enabled=settings.cortex_github_connector_enabled,
        repo_docs_connector_enabled=settings.cortex_repo_docs_connector_enabled,
        ui_enabled=settings.cortex_ui_enabled,
        internal_admin_session_enabled=settings.cortex_internal_admin_session_enabled,
        context_gate_blocking_enabled=settings.cortex_context_gate_blocking_enabled,
        embedding_mode=settings.cortex_embedding_mode,
        api_rate_limit_enabled=settings.cortex_api_rate_limit_enabled,
        provider_rate_limit_enabled=settings.cortex_provider_rate_limit_enabled,
        model_rate_limit_enabled=settings.cortex_model_rate_limit_enabled,
        cache_backend=settings.cortex_cache_backend,
    )


def validate_feature_flags(settings: Settings) -> list[str]:
    if settings.cortex_env != "production":
        return []
    return feature_flags_from_settings(settings).production_violations()
