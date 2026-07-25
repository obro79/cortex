import pytest
from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings

DEV_ENDPOINTS = (
    ("GET", "/dev/workbench"),
    ("POST", "/dev/fixtures/reset"),
    ("POST", "/dev/fixtures/seed"),
    ("POST", "/dev/pipeline/run"),
    ("GET", "/dev/pipeline/runs/run-cor-123-001"),
    ("POST", "/dev/retrieval/query"),
    ("GET", "/dev/evidence-packs/ep-cor-123"),
    ("POST", "/dev/evals/run"),
)


def test_dev_workbench_unavailable_when_disabled() -> None:
    client = TestClient(create_app(Settings(cortex_dev_workbench_enabled=False)))
    for method, path in DEV_ENDPOINTS:
        response = client.request(method, path, json={"query": "COR-123"})
        assert response.status_code == 404


def test_dev_workbench_available_when_enabled() -> None:
    client = TestClient(create_app(Settings(cortex_dev_workbench_enabled=True)))
    response = client.get("/dev/workbench")
    assert response.status_code == 200
    assert "Cortex Dev Workbench" in response.text


def test_dev_workbench_rejected_outside_local_or_test() -> None:
    with pytest.raises(ValueError, match="dev workbench cannot be enabled"):
        create_app(
            Settings(
                cortex_env="staging",
                cortex_dev_workbench_enabled=True,
            )
        )
