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
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"runtime_config": "failed"},
        "issues": [
            {
                "field": "database_url",
                "code": "missing_required_config",
                "message": "DATABASE_URL is required for this runtime role",
            }
        ],
    }


def test_ready_with_required_configured() -> None:
    client = TestClient(
        create_app(
            Settings(
                database_url="postgresql+asyncpg://cortex:cortex@postgres:5432/cortex"
            )
        )
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"runtime_config": "ok"},
        "issues": [],
    }
