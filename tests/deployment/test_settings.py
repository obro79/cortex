from cortex.config import Settings
from cortex.deployment.config import validate_runtime_config


def test_api_local_memory_mode_does_not_require_provider_credentials() -> None:
    issues = validate_runtime_config(Settings(), role="api")

    assert [issue.field for issue in issues] == ["database_url"]
    assert all("SLACK" not in issue.message for issue in issues)
    assert all("GITHUB" not in issue.message for issue in issues)
    assert all("LINEAR" not in issue.message for issue in issues)


def test_noop_worker_has_no_required_dependencies() -> None:
    issues = validate_runtime_config(Settings(), role="worker-noop")

    assert issues == []


def test_pipeline_worker_requires_database_and_kafka() -> None:
    issues = validate_runtime_config(Settings(), role="worker-pipeline")

    assert {issue.field for issue in issues} == {
        "database_url",
        "kafka_bootstrap_servers",
    }
    assert {issue.code for issue in issues} == {"missing_required_config"}


def test_kafka_runtime_requires_sql_state_backend() -> None:
    settings = Settings(
        cortex_event_bus="kafka",
        cortex_state_backend="memory",
        kafka_bootstrap_servers="kafka:9092",
        database_url="postgresql+asyncpg://cortex:cortex@postgres:5432/cortex",
    )

    issues = validate_runtime_config(settings, role="api")

    assert len(issues) == 1
    assert issues[0].field == "cortex_state_backend"
    assert issues[0].code == "invalid_runtime_config"


def test_compose_like_settings_pass_for_api_and_pipeline_worker() -> None:
    settings = Settings(
        cortex_event_bus="kafka",
        cortex_state_backend="sql",
        database_url="postgresql+asyncpg://cortex:cortex@postgres:5432/cortex",
        kafka_bootstrap_servers="kafka:9092",
    )

    assert validate_runtime_config(settings, role="api") == []
    assert validate_runtime_config(settings, role="worker-pipeline") == []
    assert validate_runtime_config(settings, role="migrate") == []
