from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def compose_config() -> dict[str, object]:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text())


def services() -> dict[str, dict[str, object]]:
    config = compose_config()
    value = config["services"]
    assert isinstance(value, dict)
    return value


def test_compose_builds_api_and_worker_from_explicit_targets() -> None:
    value = services()

    assert value["api"]["build"] == {"context": ".", "target": "api"}
    assert value["worker"]["build"] == {"context": ".", "target": "worker"}


def test_compose_api_and_worker_commands_are_explicit() -> None:
    value = services()

    assert value["api"]["command"] == (
        "uvicorn cortex.api.app:create_app --factory --host 0.0.0.0 --port 8000"
    )
    assert value["worker"]["command"] == "cortex-worker --role pipeline"
    assert value["worker-lifecycle"]["command"] == "cortex-worker --role lifecycle"
    assert value["worker-provider-acl"]["command"] == (
        "cortex-worker --role provider-acl"
    )


def test_compose_contains_current_runtime_dependencies() -> None:
    value = services()

    assert {
        "api",
        "worker",
        "worker-lifecycle",
        "worker-provider-acl",
        "postgres",
        "kafka",
        "qdrant",
        "minio",
    }.issubset(value)
    assert value["kafka"]["image"] == "apache/kafka:4.2.0"
