from __future__ import annotations

from cortex.config import Settings
from cortex.deployment.config import validate_runtime_config
from cortex.platform import feature_flags_from_settings, validate_feature_flags


def test_feature_flags_have_safe_defaults() -> None:
    flags = feature_flags_from_settings(Settings(_env_file=None))

    assert flags.dev_workbench_enabled is False
    assert flags.context_gate_blocking_enabled is False
    assert flags.embedding_mode == "deterministic"
    assert flags.cache_backend == "memory"
    assert flags.sanitized_dict()["embedding_mode"] == "deterministic"


def test_production_rejects_dev_workbench_flag() -> None:
    settings = Settings(
        _env_file=None,
        cortex_env="production",
        cortex_dev_workbench_enabled=True,
        cortex_api_rate_limit_enabled=False,
    )

    assert validate_feature_flags(settings) == ["dev_workbench_enabled"]


def test_production_rejects_memory_cache_for_rate_limits() -> None:
    settings = Settings(
        _env_file=None,
        cortex_env="production",
        cortex_dev_workbench_enabled=False,
        cortex_api_rate_limit_enabled=True,
    )

    assert validate_feature_flags(settings) == ["memory_cache_with_rate_limits"]


def test_runtime_config_surfaces_feature_flag_violations() -> None:
    issues = validate_runtime_config(
        Settings(
            _env_file=None,
            cortex_env="production",
            cortex_dev_workbench_enabled=True,
            cortex_api_rate_limit_enabled=False,
        ),
        role="worker-noop",
    )

    assert len(issues) == 1
    assert issues[0].field == "dev_workbench_enabled"
    assert issues[0].code == "unsafe_production_feature_flag"
    assert issues[0].message == "dev_workbench_enabled is not allowed in production"
