from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cortex.config import Settings

RuntimeRole = Literal["api", "worker-noop", "worker-pipeline", "migrate"]


@dataclass(frozen=True)
class RuntimeConfigIssue:
    field: str
    code: str
    message: str


def validate_runtime_config(
    settings: Settings, *, role: RuntimeRole
) -> list[RuntimeConfigIssue]:
    issues: list[RuntimeConfigIssue] = []
    if role in {"api", "worker-pipeline", "migrate"}:
        _require(settings.database_url, "database_url", "DATABASE_URL", issues)
    if role == "worker-pipeline" or settings.cortex_event_bus == "kafka":
        _require(
            settings.kafka_bootstrap_servers,
            "kafka_bootstrap_servers",
            "KAFKA_BOOTSTRAP_SERVERS",
            issues,
        )
    if settings.cortex_event_bus == "kafka":
        _require_equal(
            settings.cortex_state_backend,
            expected="sql",
            field="cortex_state_backend",
            env_name="CORTEX_STATE_BACKEND",
            issues=issues,
        )
    if settings.cortex_state_backend == "sql":
        _require(settings.database_url, "database_url", "DATABASE_URL", issues)
    if role == "worker-noop":
        return []
    if role == "api" and settings.cortex_event_bus == "memory":
        return issues
    return issues


def _require(
    value: str, field: str, env_name: str, issues: list[RuntimeConfigIssue]
) -> None:
    if value:
        return
    issues.append(
        RuntimeConfigIssue(
            field=field,
            code="missing_required_config",
            message=f"{env_name} is required for this runtime role",
        )
    )


def _require_equal(
    value: str,
    *,
    expected: str,
    field: str,
    env_name: str,
    issues: list[RuntimeConfigIssue],
) -> None:
    if value == expected:
        return
    issues.append(
        RuntimeConfigIssue(
            field=field,
            code="invalid_runtime_config",
            message=f"{env_name} must be {expected} for this runtime role",
        )
    )
