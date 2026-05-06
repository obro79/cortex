from cortex.config import Settings


def test_settings_defaults_load_without_services() -> None:
    settings = Settings()
    assert settings.cortex_env == "local"
    assert settings.database_url == ""


def test_env_overrides_apply(monkeypatch: object) -> None:
    monkeypatch.setenv("CORTEX_DEV_WORKBENCH_ENABLED", "true")
    assert Settings().cortex_dev_workbench_enabled is True


def test_sanitized_config_hides_sensitive_values(monkeypatch: object) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/db")
    sanitized = Settings().sanitized_dict()
    assert sanitized["database_url"] == "[REDACTED]"
