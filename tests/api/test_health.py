from fastapi.testclient import TestClient

from cortex.api.app import create_app
from cortex.config import Settings


def test_live_returns_liveness() -> None:
    client = TestClient(create_app(Settings()))
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_ready_without_database_configured() -> None:
    client = TestClient(create_app(Settings()))
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database_configured": False}
