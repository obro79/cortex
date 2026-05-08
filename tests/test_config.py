from cortex.config import Settings


def test_settings_defaults_load_without_services() -> None:
    settings = Settings()
    assert settings.cortex_env == "local"
    assert settings.cortex_cache_backend == "memory"
    assert settings.database_url == ""


def test_env_overrides_apply(monkeypatch: object) -> None:
    monkeypatch.setenv("CORTEX_DEV_WORKBENCH_ENABLED", "true")
    assert Settings().cortex_dev_workbench_enabled is True


def test_yaml_config_file_loads_with_env_override(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "cortex.yaml"
    config_path.write_text(
        "\n".join(
            [
                "cortex_event_bus: kafka",
                "cortex_state_backend: sql",
                "cortex_cache_backend: redis",
                "kafka_bootstrap_servers: yaml:9092",
            ]
        )
    )
    monkeypatch.setenv("CORTEX_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "env:9092")

    settings = Settings()

    assert settings.cortex_event_bus == "kafka"
    assert settings.cortex_state_backend == "sql"
    assert settings.cortex_cache_backend == "redis"
    assert settings.kafka_bootstrap_servers == "env:9092"


def test_sanitized_config_hides_sensitive_values(monkeypatch: object) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/db")
    sanitized = Settings().sanitized_dict()
    assert sanitized["database_url"] == "[REDACTED]"
