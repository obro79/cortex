from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def test_dev_workbench_unavailable_when_disabled() -> None:
    client = TestClient(create_app(Settings(cortex_dev_workbench_enabled=False)))
    assert client.get("/dev/workbench").status_code == 404


def test_dev_workbench_available_when_enabled() -> None:
    client = TestClient(create_app(Settings(cortex_dev_workbench_enabled=True)))
    response = client.get("/dev/workbench")
    assert response.status_code == 200
    assert "placeholder" in response.text
