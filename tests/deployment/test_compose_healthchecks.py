from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def services() -> dict[str, dict[str, object]]:
    config = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    value = config["services"]
    assert isinstance(value, dict)
    return value


def test_compose_defines_healthchecks_for_runtime_dependencies() -> None:
    value = services()

    for service in ("api", "postgres", "kafka", "qdrant", "minio"):
        assert "healthcheck" in value[service]


def test_api_and_worker_wait_for_healthy_dependencies() -> None:
    value = services()

    api_dependencies = value["api"]["depends_on"]
    worker_dependencies = value["worker"]["depends_on"]
    assert isinstance(api_dependencies, dict)
    assert isinstance(worker_dependencies, dict)
    assert api_dependencies["postgres"] == {"condition": "service_healthy"}
    assert api_dependencies["kafka"] == {"condition": "service_healthy"}
    assert api_dependencies["qdrant"] == {"condition": "service_healthy"}
    assert api_dependencies["minio"] == {"condition": "service_healthy"}
    assert worker_dependencies["postgres"] == {"condition": "service_healthy"}
    assert worker_dependencies["kafka"] == {"condition": "service_healthy"}


def test_compose_has_explicit_migration_service_profile() -> None:
    value = services()

    migrate = value["migrate"]
    assert migrate["command"] == "alembic upgrade head"
    assert migrate["profiles"] == ["migrate"]
    assert migrate["build"] == {"context": ".", "target": "api"}
    assert migrate["depends_on"] == {"postgres": {"condition": "service_healthy"}}
