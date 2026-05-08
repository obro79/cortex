from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs/deployment/kubernetes-boundaries.md"


def test_kubernetes_boundary_docs_map_future_probes() -> None:
    text = DOC.read_text()

    assert "`api` liveness: `GET /health/live`" in text
    assert "`api` readiness: `GET /health/ready`" in text
    assert "`worker-pipeline` liveness" in text
    assert "`worker-pipeline` readiness" in text
    assert "`migrate`: one-shot job running `alembic upgrade head`" in text


def test_kubernetes_boundary_docs_map_config_secrets_and_scaling() -> None:
    text = DOC.read_text()

    assert "ConfigMaps" in text
    assert "Secrets" in text
    assert "`api`: stateless FastAPI deployment behind ingress" in text
    assert "`worker-pipeline`: deployment scaled by Kafka consumer group" in text
    assert "Kafka consumer groups for worker distribution" in text
    assert "Postgres row-level leases" in text


def test_kubernetes_boundary_docs_are_explicitly_not_manifests() -> None:
    text = DOC.read_text()

    assert "Phase 12 does not ship Kubernetes manifests" in text
    assert "Kubernetes Deployment, Service, Ingress, Job, or Secret manifests" in text
    assert "HorizontalPodAutoscaler definitions" in text
    assert "custom leader-election controllers" in text
