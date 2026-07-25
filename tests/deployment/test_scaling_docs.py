from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs/deployment/hosted-containers.md"


def test_hosted_container_docs_name_required_env_and_secret_boundaries() -> None:
    text = DOC.read_text()

    for name in (
        "DATABASE_URL",
        "KAFKA_BOOTSTRAP_SERVERS",
        "CORTEX_STATE_BACKEND=sql",
        "CORTEX_EVENT_BUS=kafka",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
    ):
        assert name in text
    assert "Do not bake them into images" in text
    assert "API and worker startup must not run migrations implicitly" in text


def test_hosted_container_docs_name_scalable_and_stateful_services() -> None:
    text = DOC.read_text()

    assert "Horizontally scalable" in text
    assert "`api`: stateless" in text
    assert "`worker-pipeline`: scale by Kafka consumer group" in text
    assert "Stateful or managed" in text
    for service in ("Postgres", "Kafka", "object storage", "Qdrant"):
        assert service in text


def test_hosted_container_docs_include_migration_and_smoke_commands() -> None:
    text = DOC.read_text()

    assert "docker compose --profile migrate run --rm migrate" in text
    assert "python scripts/deployment_smoke.py --no-build" in text
    assert "python scripts/deployment_smoke.py --full" in text
